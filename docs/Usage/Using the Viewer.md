# Using the Viewer

The Viewer runs on the machine you're sitting at — the controller.

## Connecting

1. Open **ScreenConnect Viewer** from Applications / app launcher
2. A connect dialog appears automatically
3. Fill in:
   - **Host** — IP address of the machine running the Agent
   - **Port** — 8765 (default)
   - **Token** — the `auth.token` from the agent's config
4. Click **Connect**

The main window shows the agent's screen. You can resize the window freely — the image scales to fit.

## Controls

### Mouse

| Action | How |
|--------|-----|
| Move | Move your mouse within the viewer window |
| Left click | Left click |
| Right click | Right click |
| Middle click | Middle click |
| Scroll | Scroll wheel |
| Drag | Click and hold, move, release |
| Double-click | Double-click |

### Keyboard

Type normally. All keys are forwarded including:

- `Ctrl`, `Shift`, `Alt`
- `Cmd` (Mac viewer → Mac agent: maps to Cmd; Mac viewer → non-Mac agent: maps to Ctrl)
- Special keys: arrows, function keys, Home, End, Page Up/Down, Delete, Backspace, Escape, Enter

### Modifier combos

Standard combos like `Ctrl+C`, `Ctrl+V`, `Cmd+Tab`, `Ctrl+Shift+T` all work — the viewer captures the modifiers and sends them as a bundle.

## Toolbar

| Button | Action |
|--------|--------|
| Disconnect | Close the connection (auto-reconnects if enabled) |
| Pull Clipboard | Copy the agent's clipboard to your clipboard |
| Push Clipboard | Send your clipboard to the agent |
| Send File | Open a file picker to send a file to the agent |
| Monitor | Switch which monitor the agent streams |
| Settings | Open the settings dialog |

## Clipboard sync

See [[Clipboard Sync]] for the full workflow.

## File transfer

See [[File Transfer]] for the full workflow.

## Reconnect behaviour

If the connection drops, the viewer automatically retries with exponential back-off:

```
Attempt 1 → wait 1s → Attempt 2 → wait 2s → Attempt 3 → wait 4s → …
```

Max wait is capped at 60s. The status bar shows the retry count. To stop retrying, click **Disconnect**.

Reconnect is configurable in `config/viewer.toml`:

```toml
[reconnect]
enabled        = true
max_attempts   = 0      # 0 = try forever
initial_delay  = 1.0
max_delay      = 60.0
backoff_factor = 2.0
```

## Disconnecting manually

Click **Disconnect** in the toolbar. The window stays open — click **Connect** (in the menu or toolbar) to start a new session.
