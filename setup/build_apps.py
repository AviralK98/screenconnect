#!/usr/bin/env python3
"""
Build native launchers for ScreenConnect.

    python3 setup/build_apps.py

macOS   → ScreenConnect Agent.app  +  ScreenConnect Viewer.app  (project root)
Windows → ScreenConnect Agent.vbs  +  ScreenConnect Viewer.vbs  (project root)
           (.bat debug variants also created)
Linux   → screenconnect-agent.sh   +  screenconnect-viewer.sh   (project root)
           .desktop entries installed to ~/.local/share/applications/

Launchers point directly at the source files.
Edit code → re-open the app → changes are live. No rebuild needed.
"""
from __future__ import annotations

import os
import platform
import plistlib
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.resolve()
ICONS_DIR  = PROJECT_DIR / "setup" / "icons"
PYTHON = sys.executable   # same Python that has all requirements installed

APPS = [
    ("ScreenConnect Agent",  "agent_gui.py",  "screenconnect-agent",  "agent"),
    ("ScreenConnect Viewer", "viewer_gui.py", "screenconnect-viewer", "viewer"),
]

ICON_CONFIGS = [
    ("agent",  (76,  175,  80), "A"),   # green
    ("viewer", (74,  124, 199), "V"),   # blue
]

# ── Icon generation ───────────────────────────────────────────────────────────

def make_icons() -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  Pillow not found — skipping icons (pip install pillow to enable).")
        return

    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    for stem, color, letter in ICON_CONFIGS:
        size = 512
        img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 6,
                                fill=(*color, 255))

        font = None
        for fp in [
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]:
            try:
                font = ImageFont.truetype(fp, size // 2)
                break
            except (IOError, OSError):
                continue
        if font is None:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), letter, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]),
                  letter, fill="white", font=font)

        img.save(ICONS_DIR / f"{stem}.png")

        if sys.platform == "darwin":
            _make_icns(img, ICONS_DIR / f"{stem}.icns")

        sizes = [16, 32, 48, 64, 128, 256]
        frames = [img.resize((s, s), Image.LANCZOS) for s in sizes]
        frames[0].save(ICONS_DIR / f"{stem}.ico", format="ICO",
                       sizes=[(s, s) for s in sizes], append_images=frames[1:])

    print("  Icons generated.")


def _make_icns(img: "Image.Image", dest: Path) -> None:
    from PIL import Image
    iconset = dest.with_suffix(".iconset")
    iconset.mkdir(exist_ok=True)
    for s in [16, 32, 64, 128, 256, 512]:
        img.resize((s,   s  ), Image.LANCZOS).save(iconset / f"icon_{s}x{s}.png")
        img.resize((s*2, s*2), Image.LANCZOS).save(iconset / f"icon_{s}x{s}@2x.png")
    subprocess.run(["iconutil", "-c", "icns", str(iconset)], check=True,
                   capture_output=True)
    shutil.rmtree(iconset)


# ── macOS native launcher (C source) ──────────────────────────────────────────
# macOS 26+ rejects shell scripts as CFBundleExecutable.
# We compile a tiny native binary that reads its configuration from
# Contents/Resources/launch_args and exec's Python with the right script.

_LAUNCHER_C = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <mach-o/dyld.h>

static void strip(char *s) {
    size_t n = strlen(s);
    while (n > 0 && (s[n-1]=='\n'||s[n-1]=='\r'||s[n-1]==' ')) s[--n]='\0';
}

int main(void) {
    char exe[4096]; uint32_t sz = sizeof(exe);
    if (_NSGetExecutablePath(exe, &sz) != 0) return 1;
    char *sl = strrchr(exe, '/');
    if (!sl) return 1;
    *sl = '\0';  /* exe = .app/Contents/MacOS */

    char args[4096];
    snprintf(args, sizeof(args), "%s/../Resources/launch_args", exe);

    FILE *f = fopen(args, "r");
    if (!f) { perror("launch_args"); return 1; }

    char python[4096], script[4096], workdir[4096];
    if (!fgets(python,  sizeof(python),  f) ||
        !fgets(script,  sizeof(script),  f) ||
        !fgets(workdir, sizeof(workdir), f)) {
        fputs("launch_args: needs 3 lines\n", stderr);
        fclose(f); return 1;
    }
    fclose(f);
    strip(python); strip(script); strip(workdir);

    if (chdir(workdir) != 0) { perror("chdir"); return 1; }
    execl(python, python, script, NULL);
    perror("execl"); return 127;
}
"""


def _compile_launcher(dest: Path) -> bool:
    """Compile the C launcher. Returns True on success."""
    if not shutil.which("clang"):
        return False
    with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as tf:
        tf.write(_LAUNCHER_C)
        src = tf.name
    try:
        result = subprocess.run(
            ["clang", "-O2", "-o", str(dest), src],
            capture_output=True,
        )
        if result.returncode != 0:
            print("  clang error:", result.stderr.decode())
            return False
        return True
    finally:
        os.unlink(src)


# ── macOS ──────────────────────────────────────────────────────────────────

def build_macos() -> None:
    # Compile launcher once; reuse for both apps
    with tempfile.NamedTemporaryFile(delete=False, suffix="-launcher") as tf:
        tmp_launcher = Path(tf.name)
    compiled = _compile_launcher(tmp_launcher)
    if not compiled:
        print("  WARNING: clang not found — falling back to shell script launcher.")
        print("           Install Xcode Command Line Tools:  xcode-select --install")
        tmp_launcher.unlink(missing_ok=True)

    try:
        for app_name, script, _, icon_stem in APPS:
            app_path  = PROJECT_DIR / f"{app_name}.app"
            macos_dir = app_path / "Contents" / "MacOS"
            res_dir   = app_path / "Contents" / "Resources"
            macos_dir.mkdir(parents=True, exist_ok=True)
            res_dir.mkdir(parents=True, exist_ok=True)

            launcher = macos_dir / app_name

            if compiled:
                shutil.copy2(tmp_launcher, launcher)
                _make_executable(launcher)
                (res_dir / "launch_args").write_text(
                    f"{PYTHON}\n"
                    f"{PROJECT_DIR / script}\n"
                    f"{PROJECT_DIR}\n"
                )
            else:
                launcher.write_text(
                    "#!/bin/bash\n"
                    f"cd {_sh(PROJECT_DIR)}\n"
                    f"exec {_sh(PYTHON)} {_sh(PROJECT_DIR / script)} \"$@\"\n"
                )
                _make_executable(launcher)

            # Copy .icns into Resources so macOS picks it up
            icns_src = ICONS_DIR / f"{icon_stem}.icns"
            icns_name = f"{icon_stem}.icns"
            if icns_src.exists():
                shutil.copy2(icns_src, res_dir / icns_name)

            bundle_id = "com.screenconnect." + (
                "agent" if "Agent" in app_name else "viewer"
            )
            plist: dict = {
                "CFBundleExecutable":            app_name,
                "CFBundleIdentifier":            bundle_id,
                "CFBundleName":                  app_name,
                "CFBundleDisplayName":           app_name,
                "CFBundleVersion":               "1.0",
                "CFBundleShortVersionString":    "1.0",
                "CFBundleInfoDictionaryVersion": "6.0",
                "CFBundlePackageType":           "APPL",
                "LSMinimumSystemVersion":        "12.0",
                "NSHighResolutionCapable":       True,
                "NSPrincipalClass":              "NSApplication",
                "LSEnvironment":                 {"PYTHONDONTWRITEBYTECODE": "1"},
            }
            if icns_src.exists():
                plist["CFBundleIconFile"] = icns_name

            with open(app_path / "Contents" / "Info.plist", "wb") as f:
                plistlib.dump(plist, f)

            print(f"  ✓  {app_path.name}  ({'native binary' if compiled else 'shell script'})")
    finally:
        tmp_launcher.unlink(missing_ok=True)

    print()
    print("Drag the .app files to your Dock or /Applications.")
    print("First launch: right-click → Open  (bypasses Gatekeeper for unsigned apps).")
    print("Code changes take effect on next launch — no rebuild needed.")


# ── Windows ────────────────────────────────────────────────────────────────

def build_windows() -> None:
    pythonw = Path(PYTHON).with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = Path(PYTHON)   # fallback — console will briefly flash

    for app_name, script, _ in APPS:
        project_win = str(PROJECT_DIR)
        script_win  = str(PROJECT_DIR / script)

        # .bat — visible console, useful for debugging
        bat = PROJECT_DIR / f"{app_name}.bat"
        bat.write_text(
            "@echo off\n"
            f'cd /d "{project_win}"\n'
            f'"{PYTHON}" "{script_win}" %*\n',
            encoding="utf-8",
        )

        # .vbs — no console window, what you double-click normally
        vbs = PROJECT_DIR / f"{app_name}.vbs"
        vbs.write_text(
            'Set sh = CreateObject("WScript.Shell")\n'
            f'sh.CurrentDirectory = "{project_win}"\n'
            f'sh.Run Chr(34) & "{pythonw}" & Chr(34)'
            f' & " " & Chr(34) & "{script_win}" & Chr(34), 0\n',
            encoding="utf-8",
        )

        print(f"  ✓  {vbs.name}   (double-click — no console)")
        print(f"  ✓  {bat.name}  (debug — shows console)")

    print()
    print("Double-click the .vbs file for a clean launch.")
    print("Use the .bat file when you need to see error output.")
    print("Code changes take effect on next launch — no rebuild needed.")


# ── Linux ──────────────────────────────────────────────────────────────────

def build_linux() -> None:
    desktop_dir = Path.home() / ".local" / "share" / "applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)

    for app_name, script, desktop_id in APPS:
        # Executable shell script in project root
        sh_name = desktop_id + ".sh"
        sh_path = PROJECT_DIR / sh_name
        sh_path.write_text(
            "#!/bin/bash\n"
            f"cd {_sh(PROJECT_DIR)}\n"
            f"exec {_sh(PYTHON)} {_sh(PROJECT_DIR / script)} \"$@\"\n"
        )
        _make_executable(sh_path)

        # XDG .desktop entry
        desktop_path = desktop_dir / f"{desktop_id}.desktop"
        desktop_path.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={app_name}\n"
            f"Exec={_sh(PYTHON)} {_sh(PROJECT_DIR / script)}\n"
            "Terminal=false\n"
            "Categories=Network;RemoteAccess;\n"
            f"Comment=ScreenConnect {'server' if 'Agent' in app_name else 'viewer'}\n"
        )

        print(f"  ✓  {sh_path.name}  (run from terminal / file manager)")
        print(f"  ✓  {desktop_path}  (app menu entry)")

    if shutil.which("update-desktop-database"):
        subprocess.run(
            ["update-desktop-database", str(desktop_dir)],
            capture_output=True,
        )

    print()
    print("Shell scripts are runnable directly or from a file manager.")
    print("App menu entries are installed — may need to log out/in once.")
    print()
    print("Linux extra requirements:")
    print("  pynput keyboard/mouse control needs display access.")
    print("  If running under X11:  pip install python-xlib")
    print("  If pynput fails:       sudo usermod -aG input $USER  (then re-login)")
    print("Code changes take effect on next launch — no rebuild needed.")


# ── helpers ────────────────────────────────────────────────────────────────

def _sh(p: Path | str) -> str:
    """Single-quote a path for shell use."""
    return "'" + str(p).replace("'", "'\\''") + "'"


def _make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


# ── main ───────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"Project : {PROJECT_DIR}")
    print(f"Python  : {PYTHON}")
    print()

    print("Generating icons …")
    make_icons()
    print()

    os_name = platform.system()
    if os_name == "Darwin":
        print("Building macOS .app bundles …")
        build_macos()
    elif os_name == "Windows":
        print("Building Windows launchers …")
        build_windows()
    elif os_name == "Linux":
        print("Building Linux launchers …")
        build_linux()
    else:
        print(f"Unrecognised platform: {os_name}")
        sys.exit(1)


if __name__ == "__main__":
    main()
