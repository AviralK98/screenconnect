# Architecture Overview

## Directory structure

```
screenconnect/
├── agent_gui.py              ← Entry point: Agent GUI app
├── viewer_gui.py             ← Entry point: Viewer GUI app
├── requirements.txt
│
├── config/
│   ├── agent.toml            ← Agent defaults
│   └── viewer.toml           ← Viewer defaults
│
├── certs/                    ← TLS certs (gitignored, generate with crypto.py)
├── data/                     ← User account store (gitignored)
│
├── daemon/
│   ├── com.screenconnect.agent.plist   ← macOS launchd template
│   ├── screenconnect-agent.service     ← Linux systemd template
│   └── install_daemon.py
│
├── setup/
│   ├── build_apps.py         ← Build shell-script .app / .desktop launchers
│   └── build_dist.py         ← Build standalone apps via PyInstaller
│
└── src/
    ├── core/                 ← Shared infrastructure
    ├── agent/                ← Agent (server) logic
    ├── agent_gui/            ← Agent PyQt6 GUI
    ├── viewer/               ← Viewer (client) logic
    ├── viewer_gui/           ← Viewer PyQt6 GUI
    └── accounts/             ← User account management
```

## Two-process model

```
┌────────────────────────────┐          ┌──────────────────────────────┐
│   Agent machine            │          │   Viewer machine             │
│                            │          │                              │
│  ┌──────────────────────┐  │  wss://  │  ┌────────────────────────┐  │
│  │  ScreenConnect Agent │◄─┼──────────┼──│  ScreenConnect Viewer  │  │
│  │  (server / PyQt6)    │  │          │  │  (client / PyQt6)      │  │
│  └──────────────────────┘  │          │  └────────────────────────┘  │
│                            │          │                              │
│  Captures: screen, mouse,  │          │  Displays: screen frames     │
│  keyboard, clipboard       │          │  Sends: input, files, clip   │
└────────────────────────────┘          └──────────────────────────────┘
```

## Layer responsibilities

### `src/core/` — Shared infrastructure

| File | Responsibility |
|------|----------------|
| `config.py` | Loads TOML → typed `Config` dataclass; env var overrides via `SC_SECTION_KEY` |
| `protocol.py` | All `MessageType` enums + serialisation helpers |
| `transport.py` | `Connection` WebSocket wrapper; TLS context; binary/text lane dispatch |
| `auth.py` | `Authenticator` ABC → `TokenAuthenticator`, `UserAccountAuthenticator` |
| `session.py` | Per-connection mutable state (user, selected monitor, active transfers) |
| `feature.py` | `FeatureHandler` ABC + `FeatureRegistry` dispatcher |
| `crypto.py` | Self-signed TLS cert generation |

### `src/agent/` — Server side

| File | Responsibility |
|------|----------------|
| `server.py` | WebSocket server; auth handshake; dispatch loop |
| `features/screen.py` | Capture JPEG frames via `mss`; stream at configured FPS |
| `features/input.py` | Inject mouse/keyboard via `pynput` |
| `features/clipboard.py` | Read/write system clipboard via `pyperclip` |
| `features/files.py` | Receive chunked file transfers; SHA-256 verify; save to drop_dir |

### `src/agent_gui/` — Agent GUI (PyQt6)

| File | Responsibility |
|------|----------------|
| `app.py` | QApplication setup, dark theme, exception hook |
| `agent_window.py` | Main window: status, Start/Stop button, tabs |
| `server_worker.py` | QThread that owns the asyncio event loop and the AgentServer |
| `settings_widget.py` | Settings form (port, FPS, auth token, etc.) |
| `log_handler.py` | Python logging → Qt signal bridge |

### `src/viewer/` — Client side

| File | Responsibility |
|------|----------------|
| `client.py` | WebSocket client; reconnect loop with exponential back-off |
| `features/display.py` | Decode JPEG frames |
| `features/input.py` | Capture and forward keyboard/mouse input |
| `features/clipboard.py` | Push/pull clipboard |
| `features/files.py` | Send files in chunks; watch send_watch_dir |

### `src/viewer_gui/` — Viewer GUI (PyQt6)

| File | Responsibility |
|------|----------------|
| `app.py` | QApplication setup, dark theme, connect dialog |
| `main_window.py` | Main window: toolbar, screen area, status bar |
| `network_worker.py` | QThread that owns the asyncio loop and ViewerClient |
| `screen_widget.py` | Renders JPEG frames; captures and forwards all input events |
| `connect_dialog.py` | Host/port/token connection dialog |
| `settings_dialog.py` | Settings dialog |

## Qt ↔ asyncio bridge

The GUI runs in Qt's main thread. All network I/O runs in a `QThread` that owns its own `asyncio` event loop. Communication crosses the thread boundary via:

- **asyncio → Qt**: `pyqtSignal.emit()` (wrapped in try/except to handle object lifetime)
- **Qt → asyncio**: `loop.call_soon_threadsafe()`

## Feature/handler pattern

Every capability is a self-contained `FeatureHandler` subclass:

```python
class ClipboardFeature(FeatureHandler):
    handles = frozenset({MessageType.CLIPBOARD_REQUEST, MessageType.CLIPBOARD_DATA})

    async def on_connect(self, session, transport): ...
    async def handle(self, session, transport, msg): ...
    async def on_disconnect(self, session): ...
```

The `FeatureRegistry` routes incoming messages to the right handler. **Adding a new feature = write one class, register it. Nothing else changes.**

See [[Adding a Feature]] for the step-by-step.
