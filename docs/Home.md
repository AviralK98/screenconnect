# ScreenConnect

A self-hosted, peer-to-peer remote desktop application. Run the **Agent** on the machine you want to control; run the **Viewer** on the machine you're sitting at.

---

## Quick links

| | |
|---|---|
| [[Getting Started/Quick Start\|Quick Start]] | Up and running in 5 minutes |
| [[Getting Started/Installation - Mac\|Install on Mac]] | Build & install the .app bundles |
| [[Getting Started/Installation - Linux\|Install on Linux]] | Build & install the Linux launchers |
| [[Getting Started/Installation - Windows\|Install on Windows]] | Build & install the Windows launchers |
| [[Usage/Using the Agent\|Using the Agent]] | Start the server, manage connections |
| [[Usage/Using the Viewer\|Using the Viewer]] | Connect, control, transfer files |
| [[Architecture/Overview\|Architecture Overview]] | How everything fits together |
| [[Development/Building Apps\|Building Apps]] | Produce standalone distributable apps |
| [[Troubleshooting/Common Issues\|Troubleshooting]] | Fixes for common problems |

---

## What's implemented

- Screen sharing (JPEG, configurable FPS & quality)
- Full mouse & keyboard control (including Ctrl, Cmd, Alt, Shift modifiers)
- Clipboard sync (push & pull between agent and viewer)
- File transfer (drag-and-drop or watch folder)
- Multi-monitor selection
- Reconnect with exponential back-off
- TLS encryption (optional, self-signed cert)
- Token auth + named user accounts
- GUI apps for Agent and Viewer (PyQt6, dark theme)
- macOS .app bundles, Linux .desktop entries, Windows launchers
