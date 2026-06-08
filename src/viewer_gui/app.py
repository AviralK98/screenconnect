"""Viewer GUI entry: QApplication setup."""
from __future__ import annotations

import sys
import argparse

from PyQt6.QtWidgets import QApplication

from ..core.config import Config, get_default_config_path
from .connect_dialog import ConnectDialog
from .main_window import MainWindow
from .network_worker import NetworkWorker

DARK_STYLE = """
QMainWindow, QDialog, QWidget {
    background-color: #2b2b2b;
    color: #e0e0e0;
}
QToolBar {
    background-color: #3c3c3c;
    border-bottom: 1px solid #555;
}
QStatusBar {
    background-color: #1e1e1e;
    color: #aaa;
}
QMenuBar { background-color: #3c3c3c; color: #e0e0e0; }
QMenuBar::item:selected { background-color: #555; }
QMenu { background-color: #3c3c3c; color: #e0e0e0; border: 1px solid #555; }
QMenu::item:selected { background-color: #555; }
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #555;
    padding: 2px 4px;
    border-radius: 3px;
}
QPushButton {
    background-color: #4a7cc7;
    color: white;
    border: none;
    padding: 5px 14px;
    border-radius: 4px;
}
QPushButton:hover { background-color: #5a8cd7; }
QPushButton:disabled { background-color: #444; color: #888; }
QGroupBox {
    border: 1px solid #555;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
}
QGroupBox::title { subcontrol-origin: margin; left: 8px; color: #aaa; }
QTabWidget::pane { border: 1px solid #555; }
QTabBar::tab {
    background: #3c3c3c;
    color: #ccc;
    padding: 5px 14px;
    border: 1px solid #555;
    border-bottom: none;
}
QTabBar::tab:selected { background: #2b2b2b; color: #fff; }
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="ScreenConnect Viewer")
    parser.add_argument("--config", default=str(get_default_config_path("viewer.toml")))
    parser.add_argument("--host", help="Override agent host")
    args, _ = parser.parse_known_args()   # ignore macOS -psn_* launch args

    cfg = Config.load(args.config)
    if args.host:
        cfg.server.host = args.host

    app = QApplication(sys.argv)
    app.setApplicationName("ScreenConnect Viewer")
    app.setStyleSheet(DARK_STYLE)

    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication as _QApp

    worker = NetworkWorker()
    worker.configure(cfg)

    window = MainWindow(cfg, worker)

    # Centre on the primary screen before showing
    screen = _QApp.primaryScreen().availableGeometry()
    window.resize(1100, 700)
    window.move(
        screen.x() + (screen.width()  - window.width())  // 2,
        screen.y() + (screen.height() - window.height()) // 2,
    )
    window.show()
    app.processEvents()
    window.raise_()
    window.activateWindow()

    def _show_connect():
        dlg = ConnectDialog(cfg, window)
        if dlg.exec():
            dlg.apply_to_config()
            worker.configure(cfg)
            worker.start()
            worker.start_connection()

    # Defer the dialog until the event loop is running so the window is
    # properly on-screen and focused before the modal appears.
    QTimer.singleShot(150, _show_connect)

    # On macOS, Python re-execs itself as Python.app for GUI access, which
    # breaks bundle association. Use osascript to forcibly bring the window
    # to front once the event loop has settled.
    if sys.platform == "darwin":
        import os
        import subprocess
        pid = os.getpid()
        def _force_front():
            subprocess.Popen([
                "osascript", "-e",
                f'tell application "System Events" to set frontmost of '
                f'first process whose unix id is {pid} to true',
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        QTimer.singleShot(300, _force_front)

    sys.exit(app.exec())
