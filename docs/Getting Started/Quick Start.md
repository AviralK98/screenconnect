# Quick Start

## Prerequisites

- Python 3.11+ (3.12 recommended for standalone builds)
- The ScreenConnect repo cloned on both machines

## 1 — Install dependencies

```bash
cd screenconnect
pip install -r requirements.txt
```

## 2 — Start the Agent (machine being controlled)

Open **ScreenConnect Agent** from Applications, or run:

```bash
python3 agent_gui.py
```

Click **Start**. The status dot turns green and shows the listening port (default 8765).

## 3 — Start the Viewer (controlling machine)

Open **ScreenConnect Viewer** from Applications, or run:

```bash
python3 viewer_gui.py
```

A connect dialog appears. Enter:
- **Host** — IP address of the agent machine
- **Port** — 8765 (default)
- **Token** — must match `auth.token` in `config/agent.toml`

Click **Connect**.

---

## What you can do once connected

| Action | How |
|--------|-----|
| Move mouse | Move mouse in the viewer window |
| Click | Left/right/middle click |
| Drag | Press and hold, move, release |
| Type | Type normally — modifier keys work |
| Copy from agent | Click **Pull Clipboard** in the toolbar |
| Paste to agent | Copy something, click **Push Clipboard** |
| Send a file | Drag a file onto the viewer window |
| Switch monitor | Use the **Monitor** dropdown in the toolbar |
| Disconnect | Click **Disconnect** in the toolbar |

---

> Next: [[Installation - Mac]], [[Installation - Linux]], [[Installation - Windows]]
