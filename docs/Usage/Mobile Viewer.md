# Mobile Viewer

Control the agent machine from your **phone's web browser** — no app to install.
Works on iOS (Safari) and Android (Chrome), and from any desktop browser too.

## How it works

The agent runs a small web server that serves a viewer page. Your phone opens
that page in a browser, and the page connects back to the agent's WebSocket to
stream the screen and send touch/keyboard input. Everything reuses the same
protocol as the desktop viewer.

## Setup

1. On the agent, click **📱 Mobile** in the header
2. Check **Enable mobile web viewer**
3. The dialog shows:
   - A URL like `http://192.168.1.146:8080`
   - A **QR code** — scan it with your phone's camera
   - Your **access token**
4. On your phone, open the URL (or scan the QR), enter the token, tap **Connect**

> Both devices must be on the **same network** (same Wi-Fi).

## Touch controls

| Gesture | Action |
|---------|--------|
| **Tap** | Left click |
| **R-Click** button, then tap | Right click (one-shot) |
| **Two-finger tap** | Right click |
| **Drag** toggle on, then drag | Hold & drag (select text, move windows) |
| **Two-finger swipe** | Scroll |
| **⌨** button | Show keyboard to type |
| Drag without toggle | Move the cursor (no click) |

## Typing

Tap the **⌨** button to bring up your phone's keyboard. Typed characters,
Backspace, Enter, and arrow keys are all forwarded. On a desktop browser,
modifier combos like `Ctrl+C` work too.

## Switching monitors

If the agent has multiple monitors, a dropdown appears in the toolbar to pick
which one to view.

## Configuration

The web viewer port defaults to **8080**. Change it in `config/agent.toml`:

```toml
[server]
web_port = 8080
```

If the port is already in use, the agent shows an error — pick another port.

## Security notes

- The page is served over plain **HTTP** and connects over **`ws://`** — fine
  for a trusted local network.
- The access **token** still protects the connection: without it, a browser
  can load the page but cannot authenticate or control anything.
- **TLS (`wss://`) is not recommended for mobile** — phone browsers reject
  self-signed certificates. Keep mobile use on your local network.
- The control-permission gate still applies: on macOS the agent won't accept
  keyboard/mouse control until Accessibility is granted (see
  [[Using the Agent]]).

## Requirements

The QR code needs the optional `qrcode` package:
```bash
pip install qrcode
```
Without it, the dialog still shows the URL to type manually.
