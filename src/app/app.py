"""ScreenConnect — unified entry point.

One app, two modes. Shows a launcher to pick Agent (share this screen)
or Viewer (control another machine); either or both can be opened.
"""
from __future__ import annotations

import argparse
import logging
import sys

from PyQt6.QtWidgets import QApplication

from ..core.config import Config, get_default_config_path
from .launcher import LauncherWindow

DARK_STYLE = """
QMainWindow, QDialog, QWidget {
    background-color: #2b2b2b;
    color: #e0e0e0;
}
QToolBar { background-color: #3c3c3c; border-bottom: 1px solid #555; }
QStatusBar { background-color: #1e1e1e; color: #aaa; }
QMenuBar { background-color: #3c3c3c; color: #e0e0e0; }
QMenuBar::item:selected { background-color: #555; }
QMenu { background-color: #3c3c3c; color: #e0e0e0; border: 1px solid #555; }
QMenu::item:selected { background-color: #555; }
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #1e1e1e; color: #e0e0e0;
    border: 1px solid #555; padding: 2px 4px; border-radius: 3px;
}
QPushButton {
    background-color: #4a7cc7; color: white;
    border: none; padding: 5px 14px; border-radius: 4px;
}
QPushButton:hover { background-color: #5a8cd7; }
QPushButton:disabled { background-color: #444; color: #888; }
QGroupBox { border: 1px solid #555; border-radius: 4px; margin-top: 8px; padding-top: 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; color: #aaa; }
QTabWidget::pane { border: 1px solid #555; }
QTabBar::tab {
    background: #3c3c3c; color: #ccc;
    padding: 5px 14px; border: 1px solid #555; border-bottom: none;
}
QTabBar::tab:selected { background: #2b2b2b; color: #fff; }
QTableWidget {
    background-color: #1e1e1e; color: #ddd;
    gridline-color: #3a3a3a; alternate-background-color: #252525;
}
QHeaderView::section { background-color: #3c3c3c; color: #ccc; padding: 4px; border: none; }
QSplitter::handle { background-color: #444; }
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="ScreenConnect")
    parser.add_argument("--mode", choices=["agent", "viewer"],
                        help="Skip the launcher and open this mode directly")
    args, _ = parser.parse_known_args()   # ignore macOS -psn_* launch args

    app = QApplication(sys.argv)
    app.setApplicationName("ScreenConnect")
    app.setStyleSheet(DARK_STYLE)

    # Show any unhandled exception as a dialog instead of crashing silently.
    def _excepthook(exc_type, exc_value, exc_tb):
        import traceback
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(msg, file=sys.stderr, flush=True)
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Unhandled Error", msg)
    sys.excepthook = _excepthook

    # Shared logging → also feeds the Agent window's log pane.
    from ..agent_gui.log_handler import QtLogHandler
    qt_log = QtLogHandler()
    logging.basicConfig(
        level=logging.INFO,
        handlers=[qt_log, logging.StreamHandler(sys.stderr)],
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Keep window references alive so they aren't garbage-collected.
    windows: dict[str, object] = {"agent": None, "viewer": None}

    def open_agent() -> None:
        if windows["agent"] is None:
            from ..agent.features.input import InputFeature
            from ..agent_gui.server_worker import ServerWorker
            from ..agent_gui.agent_window import AgentWindow

            cfg = Config.load(str(get_default_config_path("agent.toml")))
            # pynput's KeyboardController must be built on the main thread.
            input_feature = InputFeature()
            worker = ServerWorker(input_feature=input_feature)
            worker.configure(cfg)
            win = AgentWindow(cfg, worker)
            qt_log.log_record.connect(win.append_log)
            windows["agent"] = win
        win = windows["agent"]
        win.show(); win.raise_(); win.activateWindow()

    def open_viewer() -> None:
        from ..viewer_gui.network_worker import NetworkWorker
        from ..viewer_gui.main_window import MainWindow
        from ..viewer_gui.connect_dialog import ConnectDialog

        if windows["viewer"] is None:
            cfg = Config.load(str(get_default_config_path("viewer.toml")))
            worker = NetworkWorker()
            worker.configure(cfg)
            win = MainWindow(cfg, worker)
            windows["viewer"] = win
            win.show(); win.raise_(); win.activateWindow()

            dlg = ConnectDialog(cfg, win)
            if dlg.exec():
                dlg.apply_to_config()
                worker.configure(cfg)
                worker.start()
                worker.start_connection()
        else:
            win = windows["viewer"]
            win.show(); win.raise_(); win.activateWindow()

    if args.mode == "agent":
        open_agent()
    elif args.mode == "viewer":
        open_viewer()
    else:
        launcher = LauncherWindow(open_agent, open_viewer)
        launcher.show()
        windows["launcher"] = launcher

    sys.exit(app.exec())
