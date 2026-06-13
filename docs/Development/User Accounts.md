# User Accounts

Beyond a shared token, the agent supports named users with bcrypt-hashed passwords.

## Enable user auth

In `config/agent.toml`:
```toml
[auth]
mode = "users"
```

## Managing users

```bash
# Add a user (prompts for password)
python3 -m src.accounts.manage adduser alice

# List users
python3 -m src.accounts.manage list

# Change password
python3 -m src.accounts.manage passwd alice

# Remove a user
python3 -m src.accounts.manage deluser alice
```

Users are stored in `data/users.json` (gitignored). Passwords are hashed with bcrypt — the plaintext is never stored.

## Viewer config for user auth

```toml
# config/viewer.toml
[auth]
mode     = "users"
username = "alice"
password = "hunter2"
```

Or leave `username`/`password` blank — the connect dialog will prompt for them.

## Mixing modes

The agent supports one mode at a time (`token` or `users`). You can't mix them — pick one and set all viewers accordingly.
