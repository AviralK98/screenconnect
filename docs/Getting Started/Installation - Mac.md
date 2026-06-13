# Installation — macOS

## Requirements

- macOS 12 or later (tested on macOS 26 / Tahoe)
- Python 3.11+ via Homebrew — `brew install python@3.14`
- Xcode Command Line Tools — `xcode-select --install`

## Install Python dependencies

```bash
cd screenconnect
pip3 install -r requirements.txt
```

## Build the .app bundles

```bash
python3 setup/build_apps.py
```

This compiles a small native C launcher (so macOS accepts it as a real binary), generates icons, and produces:

```
ScreenConnect Agent.app
ScreenConnect Viewer.app
```

## Install to /Applications

```bash
cp -R "ScreenConnect Agent.app"  /Applications/
cp -R "ScreenConnect Viewer.app" /Applications/
xattr -cr "/Applications/ScreenConnect Agent.app"
xattr -cr "/Applications/ScreenConnect Viewer.app"
```

The `xattr -cr` command removes the quarantine flag so macOS doesn't block the app.

## First launch

Because the apps are unsigned, the first launch must be done via **right-click → Open** in Finder. After that, you can open them normally from Spotlight or the Dock.

## Granting permissions

On first run the agent will ask for:
- **Screen Recording** — required to capture your screen
- **Accessibility** — required to control mouse & keyboard

Go to **System Settings → Privacy & Security** to grant both.

## Updating

The .app bundles point at the source code in the repo. To update:

```bash
git pull
```

No rebuild needed — the apps pick up changes on next launch.

## Standalone distribution (future)

Once PyInstaller supports Python 3.14, you can build a fully self-contained `.dmg` that doesn't require Python on the target machine:

```bash
# Install Python 3.12 first (PyInstaller supports it today)
brew install pyenv
pyenv install 3.12
pyenv local 3.12
pip install -r requirements.txt pyinstaller
python3 setup/build_dist.py
```

See [[Development/Building Apps]] for details.
