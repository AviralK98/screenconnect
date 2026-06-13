"""Agent main window: status, connected clients, live log, settings."""
from __future__ import annotations

import datetime

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget,
)

from ..core import permissions
from ..core.config import Config
from .log_handler import QtLogHandler
from .settings_widget import SettingsWidget
from .server_worker import ServerWorker


class AgentWindow(QMainWindow):
    def __init__(self, cfg: Config, worker: ServerWorker) -> None:
        super().__init__()
        self._cfg = cfg
        self._worker = worker
        self._start_time: datetime.datetime | None = None

        self.setWindowTitle("ScreenConnect Agent")
        self.resize(820, 580)

        self._build_ui()
        self._set_running(False)

        # ── Wire worker signals ───────────────────────────────────────────
        worker.server_started.connect(self._on_started)
        worker.server_stopped.connect(self._on_stopped)
        worker.client_connected.connect(self._on_client_connect)
        worker.client_disconnected.connect(self._on_client_disconnect)
        worker.error_occurred.connect(self._on_error)

        # ── Live control-permission indicator (macOS Accessibility) ────────
        self._perm_timer = QTimer(self)
        self._perm_timer.setInterval(1500)
        self._perm_timer.timeout.connect(self._refresh_permission)
        self._perm_timer.start()
        self._refresh_permission()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setSpacing(8)

        root_layout.addWidget(self._build_header())

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._build_tabs())
        splitter.addWidget(self._build_log_pane())
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        root_layout.addWidget(splitter)

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background-color: #1e1e1e; border-radius: 6px;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(12, 10, 12, 10)

        self._dot = QLabel("●")
        self._dot.setStyleSheet("color: #666; font-size: 18px;")
        layout.addWidget(self._dot)

        self._lbl_status = QLabel("Server not running")
        self._lbl_status.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self._lbl_status)
        layout.addStretch()

        # Control-permission warning button (macOS only; hidden when granted)
        self._btn_perm = QPushButton("⚠  Grant Control Access")
        self._btn_perm.setStyleSheet(
            "QPushButton { background-color: #c77c1e; color: white; "
            "border: none; padding: 5px 12px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #d98c2e; }"
        )
        self._btn_perm.clicked.connect(self._on_grant_clicked)
        self._btn_perm.hide()
        layout.addWidget(self._btn_perm)

        layout.addSpacing(8)

        self._lbl_clients = QLabel("0 clients")
        self._lbl_clients.setStyleSheet("color: #888;")
        layout.addWidget(self._lbl_clients)

        layout.addSpacing(16)

        self._btn_toggle = QPushButton("Start")
        self._btn_toggle.setMinimumWidth(80)
        self._btn_toggle.clicked.connect(self._toggle_server)
        layout.addWidget(self._btn_toggle)
        return w

    def _build_tabs(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.addTab(self._build_clients_tab(), "Connected Clients")
        tabs.addTab(SettingsWidget(self._cfg), "Settings")
        return tabs

    def _build_clients_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self._clients_table = QTableWidget(0, 3)
        self._clients_table.setHorizontalHeaderLabels(["Address", "User", "Connected at"])
        self._clients_table.horizontalHeader().setStretchLastSection(True)
        self._clients_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._clients_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._clients_table.setAlternatingRowColors(True)
        layout.addWidget(self._clients_table)
        return w

    def _build_log_pane(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.addWidget(QLabel("Log output"))
        clear_btn = QPushButton("Clear")
        clear_btn.setMaximumWidth(60)
        header.addStretch()
        header.addWidget(clear_btn)
        layout.addLayout(header)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(2000)
        mono = QFont("Menlo", 11) if self.fontInfo().family() else QFont("Courier New", 10)
        self._log_view.setFont(mono)
        self._log_view.setStyleSheet("background-color: #141414; color: #ccc;")
        layout.addWidget(self._log_view)

        clear_btn.clicked.connect(self._log_view.clear)
        return w

    # ── Slot handlers ──────────────────────────────────────────────────────

    @pyqtSlot(str)
    def _on_started(self, addr: str) -> None:
        self._start_time = datetime.datetime.now()
        self._set_running(True)
        self._lbl_status.setText(f"Listening on  {addr}")

    @pyqtSlot()
    def _on_stopped(self) -> None:
        self._set_running(False)
        self._lbl_status.setText("Server not running")
        self._clients_table.setRowCount(0)
        self._lbl_clients.setText("0 clients")

    @pyqtSlot(str, str)
    def _on_client_connect(self, address: str, user_label: str) -> None:
        row = self._clients_table.rowCount()
        self._clients_table.insertRow(row)
        self._clients_table.setItem(row, 0, QTableWidgetItem(address))
        self._clients_table.setItem(row, 1, QTableWidgetItem(user_label))
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._clients_table.setItem(row, 2, QTableWidgetItem(ts))
        self._update_client_count()

    @pyqtSlot(str)
    def _on_client_disconnect(self, address: str) -> None:
        for row in range(self._clients_table.rowCount()):
            item = self._clients_table.item(row, 0)
            if item and item.text() == address:
                self._clients_table.removeRow(row)
                break
        self._update_client_count()

    @pyqtSlot(str)
    def _on_error(self, msg: str) -> None:
        self._log_view.appendPlainText(f"ERROR:\n{msg}")
        self._set_running(False)
        self._lbl_status.setText("Error — see log / terminal")
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Server Error", msg)

    def append_log(self, line: str) -> None:
        self._log_view.appendPlainText(line)
        sb = self._log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ── Actions ────────────────────────────────────────────────────────────

    def _toggle_server(self) -> None:
        if self._worker.isRunning():
            self._worker.stop_server()
            self._btn_toggle.setEnabled(False)
        else:
            if not self._confirm_control_permission():
                return
            self._worker.start()

    def _confirm_control_permission(self) -> bool:
        """Check Accessibility permission before starting.

        Returns True if the server should start. When permission is
        missing, the user can still choose to start in view-only mode —
        remote control activates automatically once they grant it.
        """
        if permissions.control_granted(use_cache=False):
            return True

        # Trigger the native "allow control" prompt (no-op if already shown).
        permissions.request_control()

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Remote Control Permission Needed")
        box.setText("Keyboard & mouse control is not yet allowed.")
        box.setInformativeText(
            "macOS requires Accessibility permission before this app can "
            "control the keyboard and mouse.\n\n"
            "Viewers can still SEE this screen, but cannot control it until "
            "you grant access. Once granted, control activates automatically "
            "— no restart needed.\n\n"
            "System Settings → Privacy & Security → Accessibility → enable "
            "ScreenConnect Agent (or Python)."
        )
        open_btn  = box.addButton("Open System Settings", QMessageBox.ButtonRole.AcceptRole)
        start_btn = box.addButton("Start View-Only",       QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = box.addButton("Cancel",               QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(open_btn)
        box.exec()

        clicked = box.clickedButton()
        if clicked is cancel_btn:
            return False
        if clicked is open_btn:
            permissions.open_control_settings()
        # Both "Open Settings" and "Start View-Only" proceed to start.
        return True

    def _on_grant_clicked(self) -> None:
        permissions.request_control()
        permissions.open_control_settings()

    def _refresh_permission(self) -> None:
        granted = permissions.control_granted(use_cache=False)
        # On non-macOS there is no gate; keep the button hidden.
        if granted:
            self._btn_perm.hide()
        else:
            self._btn_perm.show()

    def _update_client_count(self) -> None:
        n = self._clients_table.rowCount()
        self._lbl_clients.setText(f"{n} client{'s' if n != 1 else ''}")

    def _set_running(self, on: bool) -> None:
        self._dot.setStyleSheet(f"color: {'#4caf50' if on else '#666'}; font-size: 18px;")
        self._btn_toggle.setText("Stop" if on else "Start")
        self._btn_toggle.setEnabled(True)

    def closeEvent(self, event) -> None:
        self._perm_timer.stop()
        self._worker.stop_server()
        self._worker.wait(2000)
        event.accept()
