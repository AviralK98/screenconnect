# ScreenConnect — Implementation Progress

Pick up from the last checked item. Each task names the exact file to create or edit.

---

## Phase 0 — Foundation

### 0.1 Directory scaffold
- [x] Create `src/`, `src/core/`, `src/agent/`, `src/agent/features/`, `src/viewer/`, `src/viewer/features/`, `src/accounts/`, `config/`, `certs/`, `data/`, `daemon/`
- [x] Add `src/__init__.py`, `src/core/__init__.py`, `src/agent/__init__.py`, `src/agent/features/__init__.py`, `src/viewer/__init__.py`, `src/viewer/features/__init__.py`, `src/accounts/__init__.py`
- [x] Add `certs/` and `data/` to `.gitignore`

### 0.2 `requirements.txt`
- [x] Create `requirements.txt` with: `websockets`, `mss`, `Pillow`, `pynput`, `opencv-python`, `numpy`, `pyperclip`, `bcrypt`, `tomli` (or `tomllib` for Python 3.11+), `watchdog`, `cryptography`

### 0.3 Config system — `src/core/config.py`
- [x] Define dataclasses: `ServerConfig`, `TLSConfig`, `AuthConfig`, `ScreenConfig`, `FilesConfig`, `ReconnectConfig`, `LoggingConfig`, root `Config`
- [x] Implement `Config.load(path)` using `tomllib` / `tomli`
- [x] Implement env var override: scan `os.environ` for `SC_<SECTION>_<KEY>`, apply to matching field
- [x] Write `config/agent.toml` with all defaults from ARCHITECTURE.md
- [x] Write `config/viewer.toml` with all defaults from ARCHITECTURE.md

### 0.4 Protocol — `src/core/protocol.py`
- [x] Define `MessageType(str, Enum)` with all 20 type strings from ARCHITECTURE.md
- [x] Define `BinaryMessageType(IntEnum)`: `FRAME = 0x01`, `FILE_CHUNK = 0x02`
- [x] Define `Message` dataclass: `type: MessageType`, `payload: dict`
- [x] Implement `Message.from_text(raw: str) -> Message` (JSON parse + validate `type` field)
- [x] Implement `Message.to_text() -> str` (JSON dump)
- [x] Implement `pack_binary(btype: BinaryMessageType, data: bytes) -> bytes`
- [x] Implement `unpack_binary(raw: bytes) -> tuple[BinaryMessageType, bytes]`
- [x] Define `BinaryFrame` dataclass: `type: BinaryMessageType`, `data: bytes`
- [x] Implement `pack_file_chunk` / `unpack_file_chunk` for binary FILE_CHUNK frames

### 0.5 Session — `src/core/session.py`
- [x] Define `Monitor` dataclass: `id`, `x`, `y`, `width`, `height`, `name`
- [x] Define `User` dataclass: `id`, `name`
- [x] Define `Session` dataclass with fields: `user`, `selected_monitor`, `monitors`, `transfer_registry`, `reconnect_status`

### 0.6 Feature base — `src/core/feature.py`
- [x] Define `FeatureHandler` ABC with `handles: frozenset[MessageType]`, `handles_binary`, `on_connect()`, `on_disconnect()`, `handle()`
- [x] Define `FeatureRegistry` with `register()`, `dispatch()`, `broadcast_connect()`, `broadcast_disconnect()`

### 0.7 Auth — `src/core/auth.py`
- [x] Define `AuthResult` dataclass: `success: bool`, `user: User | None`, `reason: str | None`
- [x] Define `Authenticator` ABC with `challenge()` (server) and `respond()` (client)
- [x] Implement `TokenAuthenticator`
- [x] Implement `UserAccountAuthenticator` (fully wired to `UserStore`)

### 0.8 Transport — `src/core/transport.py`
- [x] Define `Connection` class wrapping a `websockets` connection
- [x] Implement `send_message`, `send_binary`, `recv`, `close`
- [x] Implement `build_server_ssl_context` / `build_client_ssl_context`
- [x] Implement `verify_fingerprint` for cert pinning

### 0.9 Agent server — `src/agent/server.py`
- [x] `AgentServer`: full connection lifecycle with auth, session, feature dispatch
- [x] Auto-generates self-signed TLS cert on first run if TLS enabled

### 0.10 Viewer client — `src/viewer/client.py`
- [x] Full reconnect loop with exponential back-off
- [x] TLS + fingerprint verification
- [x] Pushes `DISPLAY_STATUS` synthetic messages during reconnect

### 0.11 Migrate existing features to new structure
- [x] `src/agent/features/screen.py` — `ScreenCaptureFeature` (capture loop + multi-monitor)
- [x] `src/agent/features/input.py` — `InputFeature` (full modifier support)
- [x] `src/viewer/features/display.py` — `DisplayFeature` (frame render + overlay)
- [x] `src/viewer/features/input.py` — `InputCaptureFeature` (keyboard + mouse + shortcuts)

### 0.12 Entry points
- [x] `agent_main.py` — all features registered, auth mode selectable
- [x] `viewer_main.py` — all features registered, monitor cycle callback wired
- [ ] Smoke test: `pip install -r requirements.txt`, run agent + viewer, verify screen share and basic input work

---

## Phase 1 — Transport Safety

### 1.1 Reconnect logic — `src/viewer/client.py`
- [ ] Add `_connect_with_retry()` loop using `cfg.reconnect` settings
- [ ] Implement exponential back-off: `delay = min(initial * factor^attempt, max_delay)`
- [ ] On each reconnect, re-run full auth + `broadcast_connect` cycle
- [ ] Add `reconnect_status: str` field to `Session`; set it to e.g. `"Reconnecting… attempt 3"` during back-off
- [ ] Push a synthetic `display_status` event so `DisplayFeature` can overlay the status string on the frame

### 1.2 TLS cert generation — `src/core/crypto.py`
- [ ] Implement `generate_self_signed(cert_path, key_path, hostname)` using `cryptography` library (add to `requirements.txt`)
- [ ] On agent startup: if `cfg.tls.enabled` and cert files don't exist, auto-generate them and log the fingerprint

### 1.3 TLS on agent — `src/agent/server.py`
- [ ] If `cfg.tls.enabled`: build `ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)`, load cert/key, pass to `websockets.serve(ssl=...)`

### 1.4 TLS on viewer — `src/viewer/client.py`
- [x] If `cfg.tls.enabled`: build `ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)`, load `ca_file` or apply fingerprint pinning, change URI scheme to `wss://`
- [x] Implement fingerprint pinning via `verify_fingerprint` in `transport.py`

---

## Phase 2 — Input Completeness

### 2.1 Modifier keys on viewer — `src/viewer/features/input.py`
- [x] `_held_modifiers: set[str]` tracking in `InputCaptureFeature`
- [x] cv2 mouse flag bits mapped to modifier names
- [x] Every key event includes current `_held_modifiers` list

### 2.2 Modifier dispatch on agent — `src/agent/features/input.py`
- [x] `MODIFIER_MAP` and `SPECIAL_KEY_MAP` dicts defined
- [x] `handle(key)`: presses modifiers, main key, releases in reverse order
- [x] Supports `key_down` / `key_up` / `press` actions
- [x] Full special key set: f1–f12, delete, home, end, page_up/down, cmd/super

---

## Phase 3 — Screen Completeness

### 3.1 Multi-monitor — `src/agent/features/screen.py`
- [x] `on_connect`: enumerates monitors, sends `monitor_list`, starts capture loop
- [x] Handles `monitor_select`: cancels current task, restarts on new monitor
- [x] `_capture_loop` uses `session.selected_monitor`

### 3.2 Monitor picker on viewer — `src/viewer/features/display.py`
- [x] Handles `monitor_list`: stores in session, overlays monitor names on screen
- [x] `Ctrl+M` in input feature → calls `monitor_cycle_cb` → sends `monitor_select`
- [x] `DISPLAY_STATUS` overlay system for status text

---

## Phase 4 — New Data Channels

### 4.1 Clipboard — `src/agent/features/clipboard.py` — [x] DONE
### 4.2 Clipboard — `src/viewer/features/clipboard.py` — [x] DONE
### 4.3 Clipboard shortcuts — `src/viewer/features/input.py`
- [x] `Ctrl+Shift+C` → `pull_clipboard` (request agent clipboard)
- [x] `Ctrl+Shift+V` → `push_clipboard` (push local clipboard to agent)

### 4.4 File transfer — `src/agent/features/files.py` — [x] DONE
### 4.5 File transfer — `src/viewer/features/files.py` — [x] DONE

---

## Phase 5 — Operations

### 5.1 Daemon — macOS launchd — [x] `daemon/com.screenconnect.agent.plist`
### 5.2 Daemon — Linux systemd — [x] `daemon/screenconnect-agent.service`
### 5.3–5.6 User accounts + auth wiring — [x] DONE
  - `src/accounts/store.py` — `UserStore` with bcrypt + atomic writes
  - `src/accounts/manage.py` — `adduser / deluser / passwd / list` CLI
  - `src/core/auth.py` — `UserAccountAuthenticator` fully implemented
  - `agent_main.py` / `viewer_main.py` — auth mode selection wired

---

## Final Checklist

- [ ] All smoke tests pass: connect, view screen, control mouse/keyboard
- [ ] TLS smoke test: enable TLS in both configs, verify connection still works
- [ ] Modifier test: Cmd+Space opens Spotlight on the agent Mac from the viewer
- [ ] Clipboard test: copy something on agent, `Ctrl+Shift+C` on viewer pastes it locally
- [ ] File transfer test: drop a file in `send_watch_dir`, verify it appears in `drop_dir`
- [ ] Multi-monitor test: `Ctrl+M` cycles through monitors
- [ ] Reconnect test: kill agent, wait, restart agent, viewer reconnects automatically
- [ ] Daemon test: `python daemon/install_daemon.py`, reboot, verify agent starts
- [ ] User accounts test: `adduser`, connect with username/password, wrong password is rejected
- [ ] Remove `mac_agent.py` and `viewer.py` (or keep as legacy aliases that print a deprecation warning)
