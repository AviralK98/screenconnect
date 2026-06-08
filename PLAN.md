# ScreenConnect — Master Plan

## What This Is

A peer-to-peer remote desktop application. A **Mac Agent** runs on the machine being controlled; a **Viewer** runs on the controlling machine. They communicate over a WebSocket connection.

Current state: two flat Python scripts (`mac_agent.py`, `viewer.py`) with no TLS, no modifier keys, no clipboard, no file transfer, no multi-monitor, no reconnect, no daemon, and no user accounts.

This plan restructures both into a proper application and implements all 8 features from `nice_to_haves.txt`.

---

## Goals

1. Implement all 8 features without breaking the existing screen-share + remote-input core.
2. Structure the code so adding a new feature means writing one module, not editing five files.
3. Make configuration explicit — no magic constants scattered through files.
4. Produce a single `ARCHITECTURE.md` that a new developer can read and immediately orient themselves.
5. Track every implementation step in `PROGRESS.md` so work can be paused and resumed.

---

## The 8 Features

### 1 — TLS Encryption
Wrap the WebSocket connection in TLS (`wss://`). The agent generates (or loads) a self-signed certificate on first run; the viewer accepts it via a pinned fingerprint stored in config.

Scope:
- `ssl.SSLContext` setup in `src/core/transport.py`
- Cert generation helper in `src/core/crypto.py`
- Config fields: `tls.cert_file`, `tls.key_file`, `tls.ca_file` (agent); `tls.fingerprint` or `tls.ca_file` (viewer)

### 2 — Keyboard Modifier Support (Ctrl, Cmd, Alt, Shift)
The current `key` event has no concept of held modifiers. The new protocol sends a `modifiers` list and separate `key_down` / `key_up` / `key_press` actions.

Scope:
- Extended `key` message schema in `src/core/protocol.py`
- Modifier tracking state machine in `src/viewer/features/input.py`
- Full modifier dispatch (including Cmd+key, Ctrl+key combos) in `src/agent/features/input.py`

### 3 — Clipboard Sync
Bidirectional clipboard sharing. Either side can push its clipboard to the peer, or request the peer's clipboard.

Scope:
- `clipboard_request` / `clipboard_data` message types
- `ClipboardFeature` on both agent and viewer sides
- Platform-specific clipboard read/write (`pyperclip` + platform fallback)

### 4 — File Transfer
Drag a file onto the viewer window → file is transferred to the agent machine (or a configured drop directory). Agent can also push files to the viewer.

Scope:
- `file_start` / `file_chunk` (binary) / `file_end` / `file_accept` / `file_reject` / `file_error` message types
- `FileTransferFeature` on both sides
- Chunked streaming to avoid loading entire file into memory
- SHA-256 checksum verification at end

### 5 — Multi-Monitor Selection
The agent advertises a list of available monitors on connect. The viewer shows a monitor picker UI and can switch monitors at any time.

Scope:
- `monitor_list` / `monitor_select` message types
- `ScreenCaptureFeature` tracks selected monitor index
- Viewer shows monitor picker in the window title bar / key shortcut

### 6 — Service / Daemon Auto-Start
The agent can be installed as a background service that starts at login / boot.

Scope:
- `daemon/com.screenconnect.agent.plist` — macOS launchd template
- `daemon/screenconnect-agent.service` — Linux systemd template
- `daemon/install_daemon.py` — installer that fills in the template and registers the service

### 7 — Reconnect Logic
The viewer automatically retries the connection on drop, with exponential back-off and a cap.

Scope:
- Reconnect loop in `src/viewer/client.py`
- Config fields: `reconnect.max_attempts`, `reconnect.initial_delay`, `reconnect.max_delay`, `reconnect.backoff_factor`
- Visual indicator in viewer window ("Reconnecting… attempt 3/10")

### 8 — User Accounts
Beyond a shared static token, the agent can have named users with hashed passwords. The viewer presents a login prompt on connect.

Scope:
- `src/accounts/store.py` — user CRUD, bcrypt password hashing, JSON file backend
- `UserAccountAuthenticator` in `src/core/auth.py`
- CLI tool: `python -m screenconnect.manage adduser <name>` / `deluser` / `passwd`
- Config field: `auth.mode = "token" | "users"`

---

## Implementation Order

Dependencies shape the order. Features that produce infrastructure come first; features that only consume it come later.

```
Phase 0: Foundation
  ├── Directory restructure + move existing code
  ├── Config system (TOML + env vars)
  └── Protocol + Transport layer (the core of everything)

Phase 1: Transport safety
  ├── Feature 7: Reconnect logic  (pure transport concern)
  └── Feature 1: TLS              (SSL wrapping of transport)

Phase 2: Input completeness
  └── Feature 2: Modifier keys    (extends existing input feature)

Phase 3: Screen completeness
  └── Feature 5: Multi-monitor    (extends existing screen feature)

Phase 4: New data channels
  ├── Feature 3: Clipboard        (new feature module, no deps)
  └── Feature 4: File transfer    (new feature module, no deps)

Phase 5: Operations
  ├── Feature 6: Daemon           (shell / config files, no code deps)
  └── Feature 8: User accounts    (extends auth layer)
```

---

## Key Design Decisions

### Feature/Handler pattern
Every capability (screen capture, input, clipboard, file transfer) is a self-contained `FeatureHandler` subclass. Both the agent server and viewer client maintain a `FeatureRegistry` that dispatches incoming messages to the right handler. Adding a new feature = write one class, register it. No existing code changes.

### Single WebSocket connection, two message lanes
All traffic shares one WebSocket connection:
- **Text frames** — JSON control messages (`{"type": "key", ...}`)
- **Binary frames** — high-throughput data; first byte identifies the type (0x01 = screen frame, 0x02 = file chunk)

### Config over constants
No hardcoded IPs, ports, tokens. Everything lives in `config/agent.toml` or `config/viewer.toml`, overridable by environment variables. The `Config` object is passed into every component.

### Auth is pluggable
`Authenticator` is an abstract base class. `TokenAuthenticator` and `UserAccountAuthenticator` are concrete implementations. The agent picks one based on `auth.mode` in config. Swapping or extending auth doesn't touch feature code.
