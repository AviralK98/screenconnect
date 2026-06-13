# Daemon Setup

Run the Agent automatically at login (macOS) or boot (Linux) so it's always available without manual intervention.

## macOS — launchd

```bash
python3 daemon/install_daemon.py
```

This fills in `daemon/com.screenconnect.agent.plist` with the correct paths and installs it to `~/Library/LaunchAgents/`. The agent starts at login and restarts automatically if it crashes.

**Manual steps:**
```bash
# Install
cp daemon/com.screenconnect.agent.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.screenconnect.agent.plist

# Start now
launchctl start com.screenconnect.agent

# Stop
launchctl stop com.screenconnect.agent

# Uninstall
launchctl unload ~/Library/LaunchAgents/com.screenconnect.agent.plist
rm ~/Library/LaunchAgents/com.screenconnect.agent.plist
```

Logs go to `~/Library/Logs/screenconnect-agent.log`.

## Linux — systemd (user service)

```bash
python3 daemon/install_daemon.py
```

Or manually:

```bash
mkdir -p ~/.config/systemd/user/
cp daemon/screenconnect-agent.service ~/.config/systemd/user/
# Edit the file to set the correct paths
systemctl --user enable screenconnect-agent
systemctl --user start screenconnect-agent
```

**Check status:**
```bash
systemctl --user status screenconnect-agent
journalctl --user -u screenconnect-agent -f
```

**To start at boot (not just login):**
```bash
loginctl enable-linger $USER
```
