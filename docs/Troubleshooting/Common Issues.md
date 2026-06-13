# Troubleshooting

## App won't open on macOS ("cannot be opened" / Gatekeeper)

The apps are unsigned. For the first launch:
1. Open **Finder → Applications**
2. **Right-click** the app → **Open**
3. Click **Open** in the security dialog

After this, future launches work normally from Spotlight or the Dock.

---

## "Spotlight does not have permission to open (null)"

This happens when launching an unsigned app via Spotlight. Use Finder right-click → Open instead. After the first approval, Spotlight works.

---

## Viewer window doesn't appear (macOS)

The process starts but the window is hidden. Look for **Python** in the Dock (macOS re-execs the app as Python.app for GUI access). Click it to bring the window forward.

If it still doesn't appear, run from terminal:
```bash
"/Applications/ScreenConnect Viewer.app/Contents/MacOS/ScreenConnect Viewer"
```
Any error will print to stdout.

---

## Agent crashes on Start (macOS) — EXC_BREAKPOINT / TSM error

The `KeyboardController` from pynput must be created on the main thread. This is already fixed in the current code — if you see this crash, make sure you're running the latest version (`git pull`).

---

## "Connection refused" when viewer tries to connect

1. Is the agent running? The status dot should be green.
2. Is the port correct? Default is 8765.
3. Is the host IP correct? On the agent machine: `ipconfig getifaddr en0` (Mac) or `ip addr show` (Linux).
4. Is a firewall blocking port 8765? On Linux: `sudo ufw allow 8765`.

---

## Keyboard / mouse control not working on Linux agent

pynput needs access to the input device group:
```bash
sudo usermod -aG input $USER
# Log out and back in
```

---

## Qt fails to start on Linux — "could not connect to display" or platform plugin error

Install the required xcb libraries:
```bash
sudo apt install libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 \
  libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 libxkbcommon-x11-0
```

---

## Screen Recording / Accessibility permission not granted (macOS)

Go to **System Settings → Privacy & Security**:
- **Screen Recording** → add ScreenConnect Agent (or Python)
- **Accessibility** → add ScreenConnect Agent (or Python)

If the app appears as "Python" in the list, that's correct — grant it there.

---

## File transfer fails / file is corrupted

The receiver verifies SHA-256. If the checksum mismatches, the file is discarded and an error is shown in the status bar. Retry the transfer. If it fails consistently, check for network packet loss.

---

## Clipboard push/pull does nothing

Both sides need `pyperclip` installed and a supported clipboard backend:
- macOS: built-in (pbcopy/pbpaste)
- Linux: install `xclip` or `xdotool` → `sudo apt install xclip`
- Windows: built-in

---

## Build fails: "PyInstaller does not support Python 3.14"

Use `build_apps.py` instead (launcher apps) — it works with any Python version. For standalone builds, install Python 3.12 via pyenv:

```bash
brew install pyenv && pyenv install 3.12 && pyenv local 3.12
pip install -r requirements.txt pyinstaller
python3 setup/build_dist.py
```

See [[Development/Building Apps]] for details.

---

## "Task was destroyed but it is pending!" in the log

This is a benign asyncio warning that can appear on disconnect. It doesn't indicate data loss or a crash. It has been mitigated in the current code.
