# File Transfer

Send files from the viewer machine to the agent machine (and vice versa).

## Sending a file to the agent

**Method 1 — Toolbar button:**
1. Click **Send File** in the viewer toolbar
2. Pick a file from the dialog
3. The status bar shows transfer progress

**Method 2 — Watch folder:**
Drop any file into the folder configured as `send_watch_dir` (default: `~/Desktop/sc_send`). The viewer detects it and automatically sends it.

```toml
# config/viewer.toml
[files]
send_watch_dir = "~/Desktop/sc_send"
```

## Where files land on the agent

Received files are saved to the agent's `drop_dir` (default: `~/Downloads/screenconnect`):

```toml
# config/agent.toml
[files]
drop_dir = "~/Downloads/screenconnect"
```

The directory is created automatically if it doesn't exist.

## Integrity check

Every transfer is verified with a SHA-256 checksum. If the received file doesn't match, the agent sends a `file_error` and the viewer shows an error in the status bar. The partial file is discarded.

## Transfer protocol

Files are sent in 64 KB chunks over the binary lane of the WebSocket:

```
viewer → agent:  file_start  { transfer_id, filename, size }
agent  → viewer: file_accept { transfer_id }
viewer → agent:  [binary]    FILE_CHUNK × N
viewer → agent:  file_end    { transfer_id, sha256_checksum }
agent  → viewer: file_error  { reason }   ← only on mismatch
```

## Limitations

- No resume on disconnect — if the connection drops mid-transfer, restart the transfer
- Single active transfer per connection
- No size limit enforced (limited by available disk on the agent)
