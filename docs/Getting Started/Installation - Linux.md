# Installation — Linux

## Requirements

- Python 3.11+
- X11 or Wayland desktop
- `clang` (for the native launcher binary)

## Install system packages

**Debian / Ubuntu:**
```bash
sudo apt install python3 python3-pip python3-venv clang \
  libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 \
  libxcb-xinerama0 libxcb-xkb1 libxkbcommon-x11-0
```

**Fedora / RHEL:**
```bash
sudo dnf install python3 python3-pip clang \
  xcb-util-cursor xcb-util-icccm xcb-util-keysyms xcb-util-wm
```

The `libxcb-*` packages are required by Qt — the app will fail to open without them.

## Install Python dependencies

```bash
cd screenconnect
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Build the launchers

```bash
python3 setup/build_apps.py
```

This creates:
- `screenconnect-agent.sh` — executable shell script
- `screenconnect-viewer.sh` — executable shell script
- `~/.local/share/applications/screenconnect-agent.desktop`
- `~/.local/share/applications/screenconnect-viewer.desktop`

Both apps will appear in your application launcher immediately.

## pynput permissions

The agent needs access to control keyboard and mouse:

```bash
sudo usermod -aG input $USER
```

Log out and back in for this to take effect. Without it, keyboard/mouse injection on the agent side will fail silently.

## Wayland note

pynput works under XWayland. If you're on a pure Wayland session and seeing issues, try:

```bash
QT_QPA_PLATFORM=xcb python3 agent_gui.py
```

## Updating

```bash
git pull
```

No rebuild needed.
