#!/usr/bin/env python3
"""
Build self-contained distributable apps using PyInstaller.

    python3 setup/build_dist.py

Output (in dist/):
  macOS   → ScreenConnect Agent.app   + ScreenConnect Agent.dmg
             ScreenConnect Viewer.app  + ScreenConnect Viewer.dmg
  Windows → ScreenConnect Agent.exe
             ScreenConnect Viewer.exe
  Linux   → screenconnect-agent
             screenconnect-viewer

Each output is fully self-contained — no Python installation needed
on the target machine.

NOTE: PyInstaller must be run on each target platform separately.
      You cannot build a Windows .exe on macOS, etc.
"""
from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT  = Path(__file__).parent.parent.resolve()
DIST     = PROJECT / "dist"
BUILD    = PROJECT / "build"
ICONS    = PROJECT / "setup" / "icons"

APPS = [
    # (display name,   entry script,       bundle id suffix, icon stem)
    ("ScreenConnect",  "screenconnect.py",  "app",            "app"),
]

# Data files to bundle into the app (the mobile web viewer page is loaded
# at runtime, so it must travel inside the .app/.exe).
DATA_FILES = [
    (str(PROJECT / "src" / "web" / "viewer.html"), "src/web"),
]

# pynput and mss load their platform backends dynamically — PyInstaller
# can't see these imports at analysis time, so we list all of them here.
# PyInstaller only bundles the ones that actually exist on the build host.
HIDDEN = [
    "pynput.keyboard._darwin",
    "pynput.keyboard._win32",
    "pynput.keyboard._xorg",
    "pynput.mouse._darwin",
    "pynput.mouse._win32",
    "pynput.mouse._xorg",
    "mss.darwin",
    "mss.windows",
    "mss.linux",
    "PIL._tkinter_finder",
    "pkg_resources.py2_warn",
]


# ── Icon generation ────────────────────────────────────────────────────────

def make_icons() -> None:
    """Create simple placeholder icons using Pillow."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("  Pillow not found — skipping icon generation (apps will use default icon).")
        return

    ICONS.mkdir(parents=True, exist_ok=True)

    configs = [
        ("app", (74, 124, 199), "S"),   # blue "S"
    ]

    for stem, color, letter in configs:
        size = 512
        img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Rounded-rectangle background
        r = size // 6
        draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=(*color, 255))

        # White letter — use default font and scale manually
        font_size = size // 2
        from PIL import ImageFont
        font = None
        for font_path in [
            "/System/Library/Fonts/Helvetica.ttc",          # macOS
            "C:/Windows/Fonts/arial.ttf",                    # Windows
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
        ]:
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except (IOError, OSError):
                continue
        if font is None:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), letter, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]),
                  letter, fill="white", font=font)

        png = ICONS / f"{stem}.png"
        img.save(png)

        # macOS .icns via iconutil
        if sys.platform == "darwin":
            _make_icns(img, ICONS / f"{stem}.icns")

        # Windows .ico (multiple sizes in one file)
        ico = ICONS / f"{stem}.ico"
        sizes = [16, 32, 48, 64, 128, 256]
        frames = [img.resize((s, s), Image.LANCZOS) for s in sizes]
        frames[0].save(ico, format="ICO", sizes=[(s, s) for s in sizes],
                       append_images=frames[1:])

    print("  Icons generated in setup/icons/")


def _make_icns(img: "Image.Image", dest: Path) -> None:
    from PIL import Image
    iconset = dest.with_suffix(".iconset")
    iconset.mkdir(exist_ok=True)
    for size in [16, 32, 64, 128, 256, 512]:
        img.resize((size, size), Image.LANCZOS).save(iconset / f"icon_{size}x{size}.png")
        img.resize((size * 2, size * 2), Image.LANCZOS).save(iconset / f"icon_{size}x{size}@2x.png")
    subprocess.run(["iconutil", "-c", "icns", str(iconset)], check=True, capture_output=True)
    shutil.rmtree(iconset)


# ── PyInstaller helpers ────────────────────────────────────────────────────

def _hidden_import_args() -> list[str]:
    args = []
    for imp in HIDDEN:
        args += ["--hidden-import", imp]
    return args


def _data_args() -> list[str]:
    # PyInstaller uses os.pathsep between src and dest ( : on POSIX, ; on Win )
    import os
    args = []
    for src, dest in DATA_FILES:
        args += ["--add-data", f"{src}{os.pathsep}{dest}"]
    return args


def _icon_arg(stem: str) -> list[str]:
    if sys.platform == "darwin":
        p = ICONS / f"{stem}.icns"
    elif sys.platform == "win32":
        p = ICONS / f"{stem}.ico"
    else:
        p = ICONS / f"{stem}.png"
    return ["--icon", str(p)] if p.exists() else []


def run_pyinstaller(app_name: str, script: str, id_suffix: str, icon_stem: str) -> None:
    os_name = platform.system()

    args = [
        str(PROJECT / script),
        "--name",      app_name,
        "--noconfirm",
        "--clean",
        "--windowed",                   # no terminal/console window
        "--collect-all", "PyQt6",       # include all Qt plugins
        "--distpath",  str(DIST),
        "--workpath",  str(BUILD),
        "--specpath",  str(BUILD),
    ] + _hidden_import_args() + _data_args() + _icon_arg(icon_stem)

    if os_name == "Darwin":
        args += ["--osx-bundle-identifier", f"com.screenconnect.{id_suffix}"]

    print(f"  Running PyInstaller for {app_name!r} …")
    import PyInstaller.__main__
    PyInstaller.__main__.run(args)


# ── Packaging ──────────────────────────────────────────────────────────────

def package_macos(app_name: str) -> None:
    """Wrap .app in a drag-to-install .dmg using hdiutil (built into macOS)."""
    app_path = DIST / f"{app_name}.app"
    if not app_path.exists():
        print(f"  WARNING: {app_path} not found, skipping DMG.")
        return

    dmg_path = DIST / f"{app_name}.dmg"
    dmg_path.unlink(missing_ok=True)

    # Temporary staging folder
    staging = DIST / "_dmg_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    shutil.copytree(app_path, staging / app_path.name)
    # Symlink to /Applications for drag-install UX
    (staging / "Applications").symlink_to("/Applications")

    subprocess.run([
        "hdiutil", "create",
        "-volname",  app_name,
        "-srcfolder", str(staging),
        "-ov", "-format", "UDZO",
        str(dmg_path),
    ], check=True, capture_output=True)

    shutil.rmtree(staging)
    print(f"  ✓  {dmg_path.name}")


def package_windows(app_name: str) -> None:
    """Zip the output directory for easy distribution."""
    out_dir = DIST / app_name
    if not out_dir.exists():
        print(f"  WARNING: {out_dir} not found.")
        return
    zip_path = DIST / app_name
    shutil.make_archive(str(zip_path), "zip", str(DIST), app_name)
    print(f"  ✓  {zip_path}.zip")


def package_linux(app_name: str) -> None:
    """Create a tarball for distribution."""
    out_dir = DIST / app_name
    if not out_dir.exists():
        print(f"  WARNING: {out_dir} not found.")
        return
    tar_path = DIST / f"{app_name}.tar.gz"
    shutil.make_archive(str(tar_path.with_suffix("").with_suffix("")), "gztar",
                        str(DIST), app_name)
    print(f"  ✓  {tar_path.name}")


# ── main ───────────────────────────────────────────────────────────────────

def main() -> None:
    os_name = platform.system()

    print(f"Platform : {os_name}")
    print(f"Python   : {sys.executable}")
    print(f"Output   : {DIST}")
    print()

    try:
        import PyInstaller
    except ImportError:
        print("ERROR: PyInstaller is not installed.")
        print("Run:  pip install pyinstaller")
        sys.exit(1)

    print("Generating icons …")
    make_icons()
    print()

    DIST.mkdir(exist_ok=True)

    for app_name, script, id_suffix, icon_stem in APPS:
        print(f"Building {app_name} …")
        run_pyinstaller(app_name, script, id_suffix, icon_stem)

        if os_name == "Darwin":
            print(f"  Packaging {app_name}.dmg …")
            package_macos(app_name)
        elif os_name == "Windows":
            package_windows(app_name)
        elif os_name == "Linux":
            package_linux(app_name)
        print()

    print("Done.")
    print()

    if os_name == "Darwin":
        print(f"  {DIST}/ScreenConnect Agent.app   — double-click or drag to /Applications")
        print(f"  {DIST}/ScreenConnect Agent.dmg   — distribute this file")
        print(f"  {DIST}/ScreenConnect Viewer.app")
        print(f"  {DIST}/ScreenConnect Viewer.dmg")
    elif os_name == "Windows":
        print(f"  {DIST}\\ScreenConnect Agent\\ScreenConnect Agent.exe")
        print(f"  {DIST}\\ScreenConnect Viewer\\ScreenConnect Viewer.exe")
        print("  (Zip files also created for distribution)")
    else:
        print(f"  {DIST}/ScreenConnect Agent/ScreenConnect Agent")
        print(f"  {DIST}/ScreenConnect Viewer/ScreenConnect Viewer")
        print("  (Tar.gz files also created for distribution)")

    print()
    print("NOTE: PyInstaller must be run on each platform separately.")
    print("      To build a Windows .exe, run this script on a Windows machine.")


if __name__ == "__main__":
    main()
