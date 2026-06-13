# ScreenConnect

A self-hosted, peer-to-peer remote desktop application built with Python and PyQt6.

Run the **Agent** on the machine you want to control. Run the **Viewer** on the machine you're sitting at. Connect over your local network or the internet.

---

## Features

- Screen sharing — JPEG, configurable FPS and quality
- Full mouse and keyboard control, including Ctrl / Cmd / Alt / Shift modifier combos
- Clipboard sync — push and pull between agent and viewer
- File transfer — drag-and-drop or auto-watched folder
- Multi-monitor selection
- Automatic reconnect with exponential back-off
- TLS encryption (optional)
- Token auth and named user accounts
- GUI apps for Agent and Viewer (dark theme, PyQt6)
- macOS .app bundles, Linux .desktop entries, Windows launchers

---

## Quick start

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Start the Agent** (machine being controlled)
```bash
python3 agent_gui.py
```
Click **Start**. Note your machine's IP address.

**3. Start the Viewer** (your machine)
```bash
python3 viewer_gui.py
```
Enter the agent's IP, port (8765), and the auth token from `config/agent.toml`. Click **Connect**.

---

## Build native apps

### macOS / Linux / Windows
```bash
python3 setup/build_apps.py
```
Produces clickable `.app` bundles (macOS), `.desktop` entries (Linux), or `.vbs` launchers (Windows) that point at this repo. No Python packaging needed — `git pull` to update.

### Install on macOS
```bash
cp -R "ScreenConnect Agent.app"  /Applications/
cp -R "ScreenConnect Viewer.app" /Applications/
xattr -cr "/Applications/ScreenConnect Agent.app"
xattr -cr "/Applications/ScreenConnect Viewer.app"
```
First launch: right-click → Open (required once for unsigned apps).

### Standalone distributable (requires Python ≤ 3.13)
```bash
pip install pyinstaller
python3 setup/build_dist.py
```
Produces a `.dmg` / `.exe` / binary with no Python dependency on the target machine. Not yet compatible with Python 3.14.

---

## Configuration

| File | Purpose |
|------|---------|
| `config/agent.toml` | Agent server settings (port, FPS, auth token, TLS) |
| `config/viewer.toml` | Viewer client settings (host, reconnect, TLS) |

Any value can be overridden with an env var: `SC_SERVER_PORT=9000`, `SC_AUTH_TOKEN=mytoken`, etc.

---

## Documentation

Full documentation is in the `docs/` folder — open it as an [Obsidian](https://obsidian.md) vault for the best experience.

| Topic | File |
|-------|------|
| Quick start | `docs/Getting Started/Quick Start.md` |
| macOS install | `docs/Getting Started/Installation - Mac.md` |
| Linux install | `docs/Getting Started/Installation - Linux.md` |
| Architecture | `docs/Architecture/Overview.md` |
| Protocol reference | `docs/Architecture/Protocol.md` |
| Config reference | `docs/Architecture/Config Reference.md` |
| Building apps | `docs/Development/Building Apps.md` |
| Adding a feature | `docs/Development/Adding a Feature.md` |
| TLS setup | `docs/Development/TLS Setup.md` |
| Daemon / auto-start | `docs/Development/Daemon Setup.md` |
| Troubleshooting | `docs/Troubleshooting/Common Issues.md` |

---

## Project structure

```
src/
├── core/          # Shared: config, protocol, transport, auth, feature registry
├── agent/         # Agent server + feature handlers (screen, input, clipboard, files)
├── agent_gui/     # Agent PyQt6 GUI
├── viewer/        # Viewer client + feature handlers
├── viewer_gui/    # Viewer PyQt6 GUI
└── accounts/      # User account store and CLI
```

## Requirements

- Python 3.11+
- See `requirements.txt` for all dependencies
