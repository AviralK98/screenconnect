"""Install the ScreenConnect agent as a system service.

macOS  : launchd user agent  (~/.LaunchAgents)
Linux  : systemd user service (~/.config/systemd/user)

Usage:
    python daemon/install_daemon.py [--install | --uninstall]
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent.resolve()
ROOT = HERE.parent

PLIST_TEMPLATE  = HERE / "com.screenconnect.agent.plist"
SERVICE_TEMPLATE = HERE / "screenconnect-agent.service"


def _fill_template(template: Path, **kwargs) -> str:
    text = template.read_text()
    for key, val in kwargs.items():
        text = text.replace("{{" + key + "}}", val)
    return text


def install_macos() -> None:
    agents_dir = Path.home() / "Library" / "LaunchAgents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    dest = agents_dir / "com.screenconnect.agent.plist"

    log_dir = Path.home() / "Library" / "Logs" / "screenconnect"
    log_dir.mkdir(parents=True, exist_ok=True)

    content = _fill_template(
        PLIST_TEMPLATE,
        PYTHON_PATH=sys.executable,
        SCRIPT_PATH=str(ROOT / "agent_main.py"),
        CONFIG_PATH=str(ROOT / "config" / "agent.toml"),
        LOG_DIR=str(log_dir),
        WORKING_DIR=str(ROOT),
    )
    dest.write_text(content)
    print(f"Wrote plist to {dest}")

    subprocess.run(["launchctl", "unload", "-w", str(dest)], capture_output=True)
    result = subprocess.run(["launchctl", "load", "-w", str(dest)], capture_output=True, text=True)
    if result.returncode == 0:
        print("Service loaded and enabled.")
    else:
        print(f"launchctl error: {result.stderr}")
        sys.exit(1)


def uninstall_macos() -> None:
    dest = Path.home() / "Library" / "LaunchAgents" / "com.screenconnect.agent.plist"
    if dest.exists():
        subprocess.run(["launchctl", "unload", "-w", str(dest)], capture_output=True)
        dest.unlink()
        print("Service removed.")
    else:
        print("Service not installed.")


def install_linux() -> None:
    service_dir = Path.home() / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)
    dest = service_dir / "screenconnect-agent.service"

    log_dir = Path.home() / ".local" / "share" / "screenconnect" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    content = _fill_template(
        SERVICE_TEMPLATE,
        PYTHON_PATH=sys.executable,
        SCRIPT_PATH=str(ROOT / "agent_main.py"),
        CONFIG_PATH=str(ROOT / "config" / "agent.toml"),
        LOG_DIR=str(log_dir),
        WORKING_DIR=str(ROOT),
    )
    dest.write_text(content)
    print(f"Wrote service to {dest}")

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", "screenconnect-agent"], check=True)
    print("Service enabled and started.")


def uninstall_linux() -> None:
    dest = Path.home() / ".config" / "systemd" / "user" / "screenconnect-agent.service"
    subprocess.run(["systemctl", "--user", "disable", "--now", "screenconnect-agent"], capture_output=True)
    if dest.exists():
        dest.unlink()
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        print("Service removed.")
    else:
        print("Service not installed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install/uninstall ScreenConnect daemon")
    parser.add_argument("--uninstall", action="store_true", help="Remove the service")
    args = parser.parse_args()

    system = platform.system()
    if system == "Darwin":
        if args.uninstall:
            uninstall_macos()
        else:
            install_macos()
    elif system == "Linux":
        if args.uninstall:
            uninstall_linux()
        else:
            install_linux()
    else:
        print(f"Unsupported platform: {system}")
        sys.exit(1)


if __name__ == "__main__":
    main()
