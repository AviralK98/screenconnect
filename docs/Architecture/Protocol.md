# Protocol Reference

All communication uses a single WebSocket connection with two message lanes.

## Text lane — JSON control messages

Shape: `{"type": "<MessageType>", ...fields}`

### Auth

| Type | Direction | Fields |
|------|-----------|--------|
| `auth` | viewer → agent | `token?: str`, `username?: str`, `password?: str` |
| `auth_ok` | agent → viewer | `user?: {id, name}` |
| `auth_fail` | agent → viewer | `reason: str` |

### Screen & monitors

| Type | Direction | Fields |
|------|-----------|--------|
| `monitor_list` | agent → viewer | `monitors: [{id, x, y, width, height, name}]` |
| `monitor_select` | viewer → agent | `monitor_id: int` |

### Input

| Type | Direction | Fields |
|------|-----------|--------|
| `mouse_move` | viewer → agent | `x: int, y: int` |
| `mouse_click` | viewer → agent | `x: int, y: int, button: "left"\|"right"\|"middle", action: "down"\|"up"` |
| `mouse_scroll` | viewer → agent | `dx: int, dy: int` |
| `key` | viewer → agent | `key: str, modifiers: str[], action: "press"\|"down"\|"up"` |

### Clipboard

| Type | Direction | Fields |
|------|-----------|--------|
| `clipboard_request` | either | _(none)_ |
| `clipboard_data` | either | `content: str` |

### File transfer

| Type | Direction | Fields |
|------|-----------|--------|
| `file_start` | sender → receiver | `transfer_id: str (UUID4), filename: str, size: int` |
| `file_end` | sender → receiver | `transfer_id: str, checksum: str (SHA-256 hex)` |
| `file_accept` | receiver → sender | `transfer_id: str` |
| `file_reject` | receiver → sender | `transfer_id: str, reason?: str` |
| `file_error` | receiver → sender | `transfer_id: str, reason: str` |

### Keep-alive

| Type | Direction | Fields |
|------|-----------|--------|
| `ping` | either | `ts: float` |
| `pong` | either | `ts: float` |

---

## Binary lane

Every binary WebSocket frame starts with a 1-byte type discriminator:

```
┌────────┬─────────────────────────────────┐
│ 1 byte │ payload                         │
│  type  │                                 │
└────────┴─────────────────────────────────┘
```

| Byte | Name | Payload |
|------|------|---------|
| `0x01` | FRAME | Raw JPEG bytes (screen frame) |
| `0x02` | FILE_CHUNK | `[36 bytes transfer_id ASCII][4 bytes chunk_index uint32 BE][data]` |

---

## Normal session flow

```
Viewer                                    Agent
  │                                         │
  │──── auth {"token": "..."}  ────────────▶│
  │◀─── auth_ok ────────────────────────────│
  │◀─── monitor_list ───────────────────────│
  │                                         │ ← _capture_loop starts
  │◀══ [0x01] JPEG frame ══════════════════│ (repeating at configured FPS)
  │                                         │
  │──── mouse_move {x, y} ─────────────────▶│
  │──── key {key:"c", modifiers:["cmd"]} ──▶│
  │                                         │
  │──── clipboard_request ─────────────────▶│
  │◀─── clipboard_data {content:"..."} ─────│
  │                                         │
  │──── file_start {transfer_id,...} ───────▶│
  │◀─── file_accept {transfer_id} ──────────│
  │══── [0x02] chunk 0 ────────────────────▶│
  │══── [0x02] chunk 1 ────────────────────▶│
  │──── file_end {checksum} ───────────────▶│
```
