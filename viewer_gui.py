"""ScreenConnect Viewer — GUI entry point.

Usage:
    python viewer_gui.py
    python viewer_gui.py --config config/viewer.toml
    python viewer_gui.py --host 192.168.1.50
"""
from src.viewer_gui.app import main

if __name__ == "__main__":
    main()
