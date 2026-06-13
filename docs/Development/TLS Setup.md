# TLS Setup

By default the connection is unencrypted. Enable TLS for secure remote access over the internet.

## Generate certificates

```bash
python3 -c "from src.core.crypto import generate_self_signed_cert; generate_self_signed_cert('certs')"
```

This creates:
```
certs/
├── agent.crt    ← Agent's certificate
├── agent.key    ← Agent's private key
└── ca.crt       ← CA cert for the viewer to pin
```

Or generate manually with openssl:

```bash
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -keyout certs/agent.key \
  -out certs/agent.crt -days 365 -nodes \
  -subj "/CN=screenconnect-agent"
cp certs/agent.crt certs/ca.crt
```

## Configure the agent

```toml
# config/agent.toml
[tls]
enabled   = true
cert_file = "certs/agent.crt"
key_file  = "certs/agent.key"
```

## Configure the viewer

**Option A — Pin by CA cert (recommended):**
```toml
# config/viewer.toml
[tls]
enabled = true
ca_file = "certs/ca.crt"
```
Copy `certs/ca.crt` from the agent machine to the viewer machine.

**Option B — Pin by fingerprint:**
```toml
# config/viewer.toml
[tls]
enabled     = true
fingerprint = "AA:BB:CC:..."   # SHA-256 fingerprint of agent.crt
```

Get the fingerprint:
```bash
openssl x509 -in certs/agent.crt -fingerprint -sha256 -noout
```

## Verify it's working

The agent log will show `wss://` instead of `ws://` when TLS is active. The viewer status bar also indicates the connection scheme.
