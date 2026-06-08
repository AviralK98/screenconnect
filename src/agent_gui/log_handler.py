"""logging.Handler that emits a Qt signal so the GUI can show live logs."""
from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, pyqtSignal


class QtLogHandler(QObject, logging.Handler):
    log_record = pyqtSignal(str)   # formatted log line

    def __init__(self, parent=None) -> None:
        QObject.__init__(self, parent)
        logging.Handler.__init__(self)
        fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
                                datefmt="%H:%M:%S")
        self.setFormatter(fmt)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record)
            self.log_record.emit(line)
        except Exception:
            self.handleError(record)
