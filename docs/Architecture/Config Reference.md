# Config Reference

Config files live in `config/`. Values can be overridden with environment variables using the pattern `SC_SECTION_KEY` (e.g. `SC_SERVER_PORT=9000`).

---

## config/agent.toml

```toml
[server]
host = "0.0.0.0"   # interface to bind; use "127.0.0.1" for local only
port = 8765

[tls]
enabled   = false
cert_file = "certs/agent.crt"
key_file  = "certs/agent.key"
# ca_file = ""     # optional CA cert for mutual TLS

[auth]
mode  = "token"              # "token" | "users"
token = "change-this-token"  # used when mode = "token"

[screen]
fps           = 12    # frames per second
jpeg_quality  = 55    # 1–95; lower = smaller, more artefacts
monitor_index = 0     # 0 = primary monitor

[files]
drop_dir = "~/Downloads/screenconnect"   # where received files are saved

[logging]
level = "INFO"   # DEBUG | INFO | WARNING | ERROR
```

---

## config/viewer.toml

```toml
[server]
host = "192.168.1.50"   # agent machine's IP address
port = 8765

[tls]
enabled = false
# ca_file    = "certs/ca.crt"   # pin agent's CA cert
# fingerprint = ""              # or pin the cert fingerprint directly

[auth]
mode  = "token"
token = "change-this-token"
# username = ""    # used when mode = "users"
# password = ""

[reconnect]
enabled        = true
max_attempts   = 0      # 0 = try forever
initial_delay  = 1.0    # seconds before first retry
max_delay      = 60.0   # cap on back-off delay
backoff_factor = 2.0    # delay multiplier per attempt

[files]
send_watch_dir = "~/Desktop/sc_send"   # files dropped here are auto-sent

[logging]
level = "INFO"
```

---

## Environment variable overrides

Any config value can be overridden without editing the file:

```bash
SC_SERVER_PORT=9000          # [server] port
SC_AUTH_TOKEN=mytoken        # [auth] token
SC_SCREEN_FPS=24             # [screen] fps
SC_TLS_ENABLED=true          # [tls] enabled
SC_LOGGING_LEVEL=DEBUG       # [logging] level
```

Pattern: `SC_<SECTION>_<KEY>` in uppercase.

---

## Frozen app config path

When running as a built app (via `build_dist.py`), config files are read from the platform config directory instead of the repo:

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/ScreenConnect/` |
| Windows | `%APPDATA%\ScreenConnect\` |
| Linux | `~/.config/ScreenConnect/` |

The directory is created automatically on first launch. If no config file exists, all defaults are used.
