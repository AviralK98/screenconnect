"""Agent GUI entry: QApplication setup."""
from __future__ import annotations

import argparse
import logging
import sys

from PyQt6.QtWidgets import QApplication

from ..core.config import Config, get_default_config_path
from ..agent.features.input import InputFeature
from .agent_window import AgentWindow
from .log_handler import QtLogHandler
from .server_worker import ServerWorker

DARK_STYLE = """
QMainWindow, QDialog, QWidget {
    background-color: #2b2b2b;
    color: #e0e0e0;
}
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
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #1e1e1e; color: #e0e0e0;
    border: 1px solid #555; padding: 2px 4px; border-radius: 3px;
}
QPushButton {
    background-color: #4a7cc7; color: white;
    border: none; padding: 5px 14px; border-radius: 4px;
}
QPushButton:hover { background-color: #5a8cd7; }
QPushButton:disabled { background-color: #444; color: #888; }
QGroupBox {
    border: 1px solid #555; border-radius: 4px;
    margin-top: 8px; padding-top: 8px;
}
QGroupBox::title { subcontrol-origin: margin; left: 8px; color: #aaa; }
QSplitter::handle { background-color: #444; }
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="ScreenConnect Agent")
    parser.add_argument("--config", default=str(get_default_config_path("agent.toml")))
    args, _ = parser.parse_known_args()   # ignore macOS -psn_* launch args

    cfg = Config.load(args.config)

    app = QApplication(sys.argv)
    app.setApplicationName("ScreenConnect Agent")
    app.setStyleSheet(DARK_STYLE)

    # Show any unhandled Python exception as a dialog instead of silent crash
    def _excepthook(exc_type, exc_value, exc_tb):
        import traceback
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(msg, file=sys.stderr, flush=True)
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Unhandled Error", msg)
    sys.excepthook = _excepthook

    qt_log = QtLogHandler()
    logging.basicConfig(
        level=getattr(logging, cfg.logging.level.upper(), logging.INFO),
        handlers=[qt_log, logging.StreamHandler(sys.stderr)],
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # pynput's KeyboardController reads keyboard layout via macOS TSM,
    # which must happen on the main thread. Create InputFeature here, then
    # pass it to ServerWorker so it never touches TSM from a background thread.
    input_feature = InputFeature()

    worker = ServerWorker(input_feature=input_feature)
    worker.configure(cfg)

    window = AgentWindow(cfg, worker)
    qt_log.log_record.connect(window.append_log)
    window.show()

    sys.exit(app.exec())
