# Installation — Windows

## Requirements

- Python 3.11+ from [python.org](https://www.python.org/downloads/) (check "Add to PATH" during install)

## Install Python dependencies

Open a terminal in the repo folder:

```cmd
pip install -r requirements.txt
```

## Build the launchers

```cmd
python setup\build_apps.py
```

This creates for each app:
- `ScreenConnect Agent.vbs` — double-click launcher (no console window)
- `ScreenConnect Agent.bat` — debug launcher (shows console, useful for errors)

## Run

Double-click the `.vbs` file for a clean launch with no console.
Use the `.bat` file if you need to see error output.

## Granting permissions

Windows may ask for firewall access when the agent first starts. Allow it on your local network.

## Updating

```cmd
git pull
```

No rebuild needed.

## Standalone .exe (future)

Once PyInstaller supports your Python version, you can build a self-contained `.exe`:

```cmd
pip install pyinstaller
python setup\build_dist.py
```

See [[Development/Building Apps]] for details.
