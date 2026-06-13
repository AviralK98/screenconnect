# Using the Agent

The Agent runs on the machine you want to control remotely.

## Starting the server

1. Open **ScreenConnect Agent** from Applications / app launcher
2. The window shows a **Start** button and a status indicator (grey = stopped)
3. Click **Start** — the dot turns green and the log shows the listening address

```
INFO  Server started on 0.0.0.0:8765
```

Give the viewer operator your local IP address (`System Settings → Wi-Fi → Details` on Mac, `ip addr` on Linux).

## Settings tab

| Setting | Description |
|---------|-------------|
| Host | Interface to bind (0.0.0.0 = all interfaces) |
| Port | Default 8765 |
| FPS | Screen capture rate. Higher = smoother but more bandwidth |
| JPEG Quality | 1–95. Lower = smaller frames, more compression artefacts |
| Monitor | Which monitor to stream (0 = primary) |
| Auth Token | Must match the token in the viewer's config |
| Auth Mode | `token` (shared secret) or `users` (named accounts) |

Changes take effect on the next **Start** — editing while running requires a Stop/Start cycle.

## Connected Clients tab

Shows a live list of connected viewers — their IP, connection time, and the authenticated user (if using user accounts).

## Log pane

All server events appear in the scrollable log at the bottom. Useful for debugging connection issues or file transfer errors.

## Stopping

Click **Stop**. All connected viewers are disconnected immediately.

## Running without the GUI

```bash
python3 agent_gui.py --config /path/to/agent.toml
```

Or run the server directly (no GUI):

```bash
# Not yet implemented as a standalone headless mode —
# use the GUI or install as a daemon
```

See [[Development/Daemon Setup]] for running the agent as a background service.

## macOS permissions required

| Permission | Why |
|------------|-----|
| Screen Recording | Capture the display to send to viewer |
| Accessibility | Inject mouse and keyboard events from the viewer |

Both are in **System Settings → Privacy & Security**.

### Control permission gate

The agent will **not** let a viewer control the keyboard and mouse until
Accessibility permission is granted. This prevents a connected viewer from
silently failing to control the machine.

- When you click **Start** without permission, a dialog appears offering to
  open System Settings. You can still **Start View-Only** so the viewer can
  see the screen.
- While permission is missing, a **⚠ Grant Control Access** button shows in
  the header. Click it to open System Settings and trigger the system prompt.
- Once you enable the agent under **Accessibility**, control activates
  **automatically within ~2 seconds** — no restart needed. The warning
  button disappears on its own.

Until granted, incoming mouse/keyboard events are dropped (and logged once),
but screen sharing, clipboard, and file transfer continue to work.
