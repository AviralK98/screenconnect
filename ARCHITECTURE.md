# ScreenConnect — Architecture

## Directory Tree

```
screenconnect/
├── PLAN.md                         # Goals, feature scope, implementation order
├── ARCHITECTURE.md                 # This file: structure, protocol, data flow
├── PROGRESS.md                     # Step-by-step implementation checklist
├── requirements.txt                # All Python dependencies
│
├── agent_main.py                   # Entry point: python agent_main.py [--config path]
├── viewer_main.py                  # Entry point: python viewer_main.py [--config path] [--host ip]
│
├── config/
│   ├── agent.toml                  # Agent defaults (overridden by env vars)
│   └── viewer.toml                 # Viewer defaults (overridden by env vars)
│
├── certs/                          # TLS certificates — gitignored
│   ├── agent.crt
│   ├── agent.key
│   └── ca.crt                      # CA cert for viewer to pin against
│
├── data/
│   └── users.json                  # User account store — gitignored
│
├── daemon/
│   ├── com.screenconnect.agent.plist    # macOS launchd template
│   ├── screenconnect-agent.service      # Linux systemd template
│   └── install_daemon.py               # Fills template, registers service
│
└── src/
    ├── __init__.py
    │
    ├── core/                       # Shared by both agent and viewer
    │   ├── __init__.py
    │   ├── config.py               # Config loader: TOML + env var overrides
    │   ├── protocol.py             # All message types + serialization
    │   ├── transport.py            # WebSocket wrapper: TLS, reconnect, dispatch
    │   ├── auth.py                 # Authenticator ABC + Token + UserAccount impls
    │   ├── session.py              # Per-connection mutable state
    │   ├── feature.py              # FeatureHandler ABC + FeatureRegistry
    │   └── crypto.py               # TLS cert generation helpers
    │
    ├── agent/
    │   ├── __init__.py
    │   ├── server.py               # AgentServer: runs WebSocket server, owns registry
    │   └── features/
    │       ├── __init__.py
    │       ├── screen.py           # ScreenCaptureFeature: capture + multi-monitor
    │       ├── input.py            # InputFeature: mouse + keyboard + full modifiers
    │       ├── clipboard.py        # ClipboardFeature (agent side)
    │       └── files.py            # FileTransferFeature (agent side: receive)
    │
    ├── viewer/
    │   ├── __init__.py
    │   ├── client.py               # ViewerClient: connects, auth, owns registry, reconnect loop
    │   └── features/
    │       ├── __init__.py
    │       ├── display.py          # DisplayFeature: render frames, monitor picker
    │       ├── input.py            # InputCaptureFeature: capture keyboard/mouse + modifiers
    │       ├── clipboard.py        # ClipboardFeature (viewer side)
    │       └── files.py            # FileTransferFeature (viewer side: send)
    │
    └── accounts/
        ├── __init__.py
        ├── store.py                # UserStore: JSON file backend, bcrypt hashing
        └── manage.py               # CLI: adduser / deluser / passwd / list
```

---

## Layer Responsibilities

### `src/core/` — Infrastructure

**`config.py`**
Loads a TOML file into a typed `Config` dataclass. Any key can be overridden by an environment variable using the pattern `SC_SECTION_KEY` (e.g., `SC_SERVER_PORT=9000`). The `Config` object is created once at startup and passed into every component; no global state.

```python
# Usage
cfg = Config.load("config/agent.toml")
cfg.server.port     # int
cfg.tls.cert_file   # Path | None
cfg.auth.mode       # "token" | "users"
```

**`protocol.py`**
Single source of truth for every message that travels over the wire. Defines:
- `MessageType` enum (all type strings)
- `Message` dataclass with `type` + `payload` dict
- `BinaryMessageType` enum (0x01 = FRAME, 0x02 = FILE_CHUNK)
- `Message.to_bytes()` / `Message.from_text()` — JSON lane
- `pack_binary(type, data)` / `unpack_binary(raw)` — binary lane

New feature = add entries here. Nothing else needs to change to support routing.

**`transport.py`**
`Connection` wraps a live WebSocket. Responsibilities:
- Sends/receives `Message` or raw binary using the two-lane protocol above
- Builds the `ssl.SSLContext` from config (TLS feature)
- Exposes `send(msg)`, `recv() -> Message | BinaryFrame`, `close()`

`ClientTransport(Connection)` adds:
- `connect(uri)` coroutine that retries with exponential back-off (reconnect feature)
- Fires `on_connected` / `on_disconnected` callbacks so the feature registry can reset

**`auth.py`**
```python
class Authenticator(ABC):
    @abstractmethod
    async def challenge(self, transport: Connection) -> AuthResult:
        """Server side: read auth message, validate, return result."""

    @abstractmethod
    async def respond(self, transport: Connection, credentials: dict) -> AuthResult:
        """Client side: send credentials, read server response."""

class TokenAuthenticator(Authenticator): ...       # uses config token
class UserAccountAuthenticator(Authenticator): ... # uses UserStore
```

`AuthResult` carries `success: bool`, `user: User | None`, `reason: str | None`.

**`session.py`**
Mutable per-connection state shared across feature handlers during a session:
```python
@dataclass
class Session:
    user: User | None           # populated after successful auth
    selected_monitor: int       # index into monitors list (default 0)
    monitors: list[Monitor]     # populated on connect from agent
    transfer_registry: dict     # active FileTransfer objects keyed by transfer_id
```

**`feature.py`**
```python
class FeatureHandler(ABC):
    # Declare which message types this handler owns
    handles: frozenset[MessageType] = frozenset()

    async def on_connect(self, session: Session, transport: Connection): ...
    async def on_disconnect(self, session: Session): ...
    async def handle(self, session: Session, transport: Connection, msg: Message): ...

class FeatureRegistry:
    def register(self, handler: FeatureHandler): ...
    async def dispatch(self, session, transport, msg): ...
    async def broadcast_connect(self, session, transport): ...
    async def broadcast_disconnect(self, session): ...
```

`on_connect` is where a feature starts its own async tasks (e.g., screen capture loop). `on_disconnect` cancels them.

---

### `src/agent/` — Server side

**`server.py`**
Creates the WebSocket server with the TLS context from config. For each new connection:
1. Instantiates a `Session`
2. Runs `Authenticator.challenge()` — closes on failure
3. Calls `registry.broadcast_connect(session, transport)`
4. Reads messages in a loop, dispatches via `registry.dispatch()`
5. On disconnect: `registry.broadcast_disconnect(session)`

**`features/screen.py` — `ScreenCaptureFeature`**
- `on_connect`: reads `cfg.screen.monitor_index`, calls `mss` to enumerate monitors, sends `monitor_list` message, starts `_capture_loop` task
- `handle(monitor_select)`: updates `session.selected_monitor`, restarts capture loop on the new monitor
- `_capture_loop`: grabs JPEG frame, sends as `BinaryFrame(FRAME, jpeg_bytes)` at configured FPS

**`features/input.py` — `InputFeature`**
- `handle(mouse_move | mouse_click | mouse_scroll)`: unchanged from current logic
- `handle(key)`: reads `modifiers` list from message, presses modifier keys first using pynput's `Key` enum, then the main key, then releases all in reverse order. Handles `key_down` / `key_up` / `key_press` actions separately for sticky modifiers.

Modifier mapping:
```python
MODIFIER_MAP = {
    "ctrl":  Key.ctrl,
    "cmd":   Key.cmd,   # macOS only
    "alt":   Key.alt,
    "shift": Key.shift,
    "super": Key.cmd,   # alias
}
```

**`features/clipboard.py` — `ClipboardFeature` (agent)**
- `handle(clipboard_request)`: reads local clipboard via `pyperclip.paste()`, sends `clipboard_data`
- `handle(clipboard_data)`: writes received content to local clipboard via `pyperclip.copy()`

**`features/files.py` — `FileTransferFeature` (agent)**
- `handle(file_start)`: records transfer metadata in `session.transfer_registry`, sends `file_accept`
- `handle(BinaryFrame(FILE_CHUNK, ...))`: appends chunk to temp file
- `handle(file_end)`: verifies SHA-256, moves temp file to `cfg.files.drop_dir`; sends `file_error` on mismatch

---

### `src/viewer/` — Client side

**`client.py`**
Owns the reconnect loop:
```
connect → auth → broadcast_connect → message loop → on_disconnect → wait(back-off) → repeat
```
Reconnect config: `initial_delay=1s`, `max_delay=60s`, `backoff_factor=2`, `max_attempts=0` (0 = infinite).
Displays reconnect status by pushing a synthetic `display_status` event into the display feature.

**`features/display.py` — `DisplayFeature`**
- `on_connect`: calls `cv2.namedWindow`, registers mouse callback
- `handle(monitor_list)`: stores list, shows monitor picker (title bar legend or overlay text)
- `handle(BinaryFrame(FRAME, ...))`: decodes JPEG, calls `cv2.imshow`; overlays reconnect status if set

**`features/input.py` — `InputCaptureFeature`**
Tracks held modifier keys using a `set[str]`. On every key event from cv2:
- Check for modifier key codes (mapped from cv2 extended key flags) and add/remove from the held set
- Send `{"type": "key", "key": ..., "modifiers": [...], "action": "press"}`

Mouse events: same as current but sends scroll as `{"type": "mouse_scroll", "dx": ..., "dy": ...}` (cv2 scroll wheel already supported via `EVENT_MOUSEWHEEL`).

**`features/clipboard.py` — `ClipboardFeature` (viewer)**
- Keyboard shortcut Ctrl+Shift+C: send `clipboard_request` to agent
- Keyboard shortcut Ctrl+Shift+V: read local clipboard, send `clipboard_data` to agent
- `handle(clipboard_data)`: write received content to local clipboard

**`features/files.py` — `FileTransferFeature` (viewer)**
- Watches a configurable `cfg.files.send_watch_dir` for new files (via `watchdog` or polling)
- On new file: send `file_start`, then stream binary chunks (default 64 KB), then `file_end` with checksum
- `handle(file_accept | file_reject | file_error)`: update UI / log

---

### `src/accounts/` — User management

**`store.py`**
```python
@dataclass
class User:
    id: str
    name: str
    password_hash: str   # bcrypt
    created_at: str      # ISO8601

class UserStore:
    def __init__(self, path: Path): ...
    def add(self, name: str, password: str) -> User: ...
    def remove(self, name: str): ...
    def verify(self, name: str, password: str) -> User | None: ...
    def list(self) -> list[User]: ...
```

Backed by a single `data/users.json` file. All writes are atomic (write to `.tmp`, then `os.replace`).

**`manage.py`**
CLI invoked via `python -m screenconnect.manage`:
```
adduser <name>    — prompts for password, adds user
deluser <name>    — removes user
passwd  <name>    — changes password
list              — lists all users
```

---

## Message Protocol

### Text lane (JSON)

All text-frame messages have the shape `{"type": "<MessageType>", ...fields}`.

| `type`            | Direction         | Fields |
|-------------------|-------------------|--------|
| `auth`            | viewer → agent    | `token?: str`, `username?: str`, `password?: str` |
| `auth_ok`         | agent → viewer    | `user?: {id, name}` |
| `auth_fail`       | agent → viewer    | `reason: str` |
| `monitor_list`    | agent → viewer    | `monitors: [{id, x, y, width, height, name}]` |
| `monitor_select`  | viewer → agent    | `monitor_id: int` |
| `mouse_move`      | viewer → agent    | `x: int, y: int` |
| `mouse_click`     | viewer → agent    | `x: int, y: int, button: "left"\|"right"\|"middle", action: "down"\|"up"\|"click"` |
| `mouse_scroll`    | viewer → agent    | `dx: int, dy: int` |
| `key`             | viewer → agent    | `key: str, modifiers: str[], action: "press"\|"down"\|"up"` |
| `clipboard_request` | either          | _(no fields)_ |
| `clipboard_data`  | either            | `content: str, mime: "text/plain"\|"image/png"` |
| `file_start`      | either            | `transfer_id: str (UUID4), filename: str, size: int, mime?: str` |
| `file_end`        | sender → receiver | `transfer_id: str, checksum: str (SHA-256 hex)` |
| `file_accept`     | receiver → sender | `transfer_id: str` |
| `file_reject`     | receiver → sender | `transfer_id: str, reason?: str` |
| `file_error`      | receiver → sender | `transfer_id: str, reason: str` |
| `ping`            | either            | `ts: float` |
| `pong`            | either            | `ts: float` |

### Binary lane

Every binary WebSocket frame starts with a 1-byte type discriminator:

```
┌────────┬─────────────────────────────────────────────────────┐
│ 1 byte │ payload                                             │
│ type   │                                                     │
└────────┴─────────────────────────────────────────────────────┘
```

| Type byte | Name        | Payload layout |
|-----------|-------------|----------------|
| `0x01`    | FRAME       | Raw JPEG bytes |
| `0x02`    | FILE_CHUNK  | `[36 bytes transfer_id ASCII][4 bytes chunk_index uint32 BE][data bytes]` |

---

## Config Schema

### `config/agent.toml`
```toml
[server]
host = "0.0.0.0"
port = 8765

[tls]
enabled = false
cert_file = "certs/agent.crt"
key_file  = "certs/agent.key"
# ca_file = ""   # optional: for client cert verification

[auth]
mode  = "token"   # "token" | "users"
token = "change-this-token"

[screen]
fps           = 12
jpeg_quality  = 55
monitor_index = 0   # default monitor (0 = primary)

[files]
drop_dir = "~/Downloads/screenconnect"

[logging]
level = "INFO"
```

### `config/viewer.toml`
```toml
[server]
host = "192.168.1.50"
port = 8765

[tls]
enabled     = false
# ca_file   = "certs/ca.crt"     # pin agent's CA cert
# fingerprint = ""               # alternative: pin cert fingerprint

[auth]
mode     = "token"
token    = "change-this-token"
# username = ""
# password = ""

[reconnect]
enabled        = true
max_attempts   = 0      # 0 = infinite
initial_delay  = 1.0    # seconds
max_delay      = 60.0
backoff_factor = 2.0

[files]
send_watch_dir = "~/Desktop/sc_send"   # files dropped here are sent to agent

[logging]
level = "INFO"
```

---

## Data Flow

### Normal session (after auth)

```
Viewer                                    Agent
  │                                         │
  │──── auth {"token": ...} ───────────────▶│
  │◀─── auth_ok ────────────────────────────│
  │◀─── monitor_list {monitors: [...]} ─────│
  │                                         │──── _capture_loop starts
  │◀═══ [binary 0x01] JPEG frame ═══════════│ (repeating)
  │◀═══ [binary 0x01] JPEG frame ═══════════│
  │                                         │
  │──── mouse_move {x, y} ─────────────────▶│ → pynput.mouse.position
  │──── key {key:"a", modifiers:["cmd"]} ──▶│ → press Cmd, press a, release a, release Cmd
  │                                         │
  │──── monitor_select {monitor_id: 2} ────▶│ → _capture_loop restarts on monitor 2
  │                                         │
  │──── clipboard_request ─────────────────▶│ → pyperclip.paste()
  │◀─── clipboard_data {content: "..."} ────│
  │                                         │
  │──── file_start {transfer_id, ...} ─────▶│
  │◀─── file_accept {transfer_id} ──────────│
  │══── [binary 0x02] chunk 0 ─────────────▶│
  │══── [binary 0x02] chunk 1 ─────────────▶│
  │──── file_end {checksum} ───────────────▶│ → verify SHA-256, move to drop_dir
```

### Reconnect flow (viewer)

```
ViewerClient
  │
  ├─ attempt 1: connect → auth → session …
  │    │
  │    └─ connection drops
  │
  ├─ wait 1s (initial_delay)
  ├─ attempt 2: reconnect
  │    └─ connection drops immediately
  │
  ├─ wait 2s
  ├─ attempt 3: reconnect → auth → session …
  │    └─ runs normally
```

---

## Extending the Application

### Adding a new feature

1. Add one or more entries to `MessageType` enum in `src/core/protocol.py`.
2. Write `src/agent/features/my_feature.py` subclassing `FeatureHandler`.
   - Set `handles = frozenset({MessageType.MY_TYPE})`.
   - Implement `handle()`, and optionally `on_connect()` / `on_disconnect()`.
3. Write the corresponding `src/viewer/features/my_feature.py`.
4. Register both in `agent_main.py` and `viewer_main.py`.
5. Add any new config fields to the TOML schemas.

That is the entire surface area of a feature addition. No other file needs editing.

### Replacing the display backend

`DisplayFeature` owns all OpenCV calls. To swap to a different GUI toolkit, only `src/viewer/features/display.py` and `src/viewer/features/input.py` change.

### Supporting Windows as an agent

`InputFeature` on the agent side uses `pynput`, which is cross-platform. `ScreenCaptureFeature` uses `mss`, also cross-platform. The only macOS-specific thing is `Key.cmd`; a platform check produces `Key.ctrl` on Windows/Linux.
