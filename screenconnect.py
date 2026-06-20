"""ScreenConnect — unified GUI entry point (Agent + Viewer in one app).

Usage:
    python screenconnect.py                 # launcher (pick a mode)
    python screenconnect.py --mode agent    # open Agent directly
    python screenconnect.py --mode viewer   # open Viewer directly
"""
from src.app.app import main

if __name__ == "__main__":
    main()
