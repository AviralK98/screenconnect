"""ScreenConnect Agent — GUI entry point.

Usage:
    python agent_gui.py
    python agent_gui.py --config config/agent.toml
"""
from src.agent_gui.app import main

if __name__ == "__main__":
    main()
