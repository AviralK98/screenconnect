"""Main viewer window: toolbar + screen area + status bar."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QLabel, QMainWindow,
    QMessageBox, QSizePolicy, QStatusBar, QToolBar, QWidget,
)

from ..core.config import Config
from ..core.protocol import MessageType
from .connect_dialog import ConnectDialog
from .screen_widget import ScreenWidget
from .settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self, cfg: Config, worker) -> None:
        super().__init__()
        self._cfg = cfg
        self._worker = worker
        self._connected = False

        self.setWindowTitle("ScreenConnect")
        self.resize(1280, 760)

        self._screen = ScreenWidget(worker.send_input)
        self.setCentralWidget(self._screen)

        self._build_toolbar()
        self._build_statusbar()
        self._build_menu()
        self._set_connected(False)

        # ── Wire worker signals ───────────────────────────────────────────
        worker.frame_received.connect(self._on_frame)
        worker.connected.connect(self._on_connected)
        worker.disconnected.connect(self._on_disconnected)
        worker.monitor_list_changed.connect(self._on_monitor_list)
        worker.clipboard_received.connect(self._on_clipboard)
        worker.status_changed.connect(self._on_status)
        worker.fps_updated.connect(self._on_fps)
        worker.file_status.connect(self._on_file_status)

    # ── UI construction ────────────────────────────────────────────────────

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setStyleSheet("QToolBar { spacing: 6px; padding: 4px; }")
        self.addToolBar(tb)

        self._act_connect = QAction("Connect", self)
        self._act_connect.setToolTip("Open connection dialog")
        self._act_connect.triggered.connect(self._show_connect_dialog)
        tb.addAction(self._act_connect)

        self._act_disconnect = QAction("Disconnect", self)
        self._act_disconnect.setToolTip("Disconnect from agent")
        self._act_disconnect.triggered.connect(self._worker.stop_connection)
        tb.addAction(self._act_disconnect)

        tb.addSeparator()

        tb.addWidget(QLabel("Monitor:"))
        self._monitor_combo = QComboBox()
        self._monitor_combo.setMinimumWidth(130)
        self._monitor_combo.currentIndexChanged.connect(self._on_monitor_selected)
        tb.addWidget(self._monitor_combo)

        tb.addSeparator()

        self._act_pull_clip = QAction("📋 Pull Clipboard", self)
        self._act_pull_clip.setToolTip("Copy agent clipboard → local (Ctrl+Shift+C)")
        self._act_pull_clip.triggered.connect(self._worker.pull_clipboard)
        tb.addAction(self._act_pull_clip)

        self._act_push_clip = QAction("📋 Push Clipboard", self)
        self._act_push_clip.setToolTip("Copy local clipboard → agent (Ctrl+Shift+V)")
        self._act_push_clip.triggered.connect(self._worker.push_clipboard)
        tb.addAction(self._act_push_clip)

        tb.addSeparator()

        self._act_send_file = QAction("📁 Send File", self)
        self._act_send_file.setToolTip("Send a file to the agent")
        self._act_send_file.triggered.connect(self._pick_and_send_file)
        tb.addAction(self._act_send_file)

        # Spacer to right-align settings
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        self._act_settings = QAction("⚙ Settings", self)
        self._act_settings.triggered.connect(self._show_settings)
        tb.addAction(self._act_settings)

    def _build_statusbar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)

        self._lbl_status   = QLabel("Disconnected")
        self._lbl_fps      = QLabel("-- fps")
        self._lbl_monitor  = QLabel("")

        sb.addWidget(self._lbl_status)
        sb.addPermanentWidget(self._lbl_monitor)
        sb.addPermanentWidget(self._lbl_fps)

    def _build_menu(self) -> None:
        menu = self.menuBar()

        file_m = menu.addMenu("File")
        file_m.addAction(self._act_connect)
        file_m.addAction(self._act_disconnect)
        file_m.addSeparator()
        quit_act = QAction("Quit", self)
        quit_act.setShortcut("Ctrl+Q")
        quit_act.triggered.connect(self.close)
        file_m.addAction(quit_act)

        edit_m = menu.addMenu("Edit")
        edit_m.addAction(self._act_pull_clip)
        edit_m.addAction(self._act_push_clip)
        edit_m.addSeparator()
        edit_m.addAction(self._act_settings)

    # ── Slot handlers ──────────────────────────────────────────────────────

    @pyqtSlot(bytes)
    def _on_frame(self, data: bytes) -> None:
        self._screen.update_frame(data)

    @pyqtSlot(str)
    def _on_connected(self, addr: str) -> None:
        self._set_connected(True)
        self._lbl_status.setText(f"Connected  {addr}")

    @pyqtSlot(str)
    def _on_disconnected(self, reason: str) -> None:
        self._set_connected(False)
        self._lbl_status.setText("Disconnected")
        self._lbl_fps.setText("-- fps")
        self._lbl_monitor.setText("")
        self._monitor_combo.clear()

    @pyqtSlot(list)
    def _on_monitor_list(self, monitors: list) -> None:
        self._monitor_combo.blockSignals(True)
        self._monitor_combo.clear()
        for m in monitors:
            self._monitor_combo.addItem(m.get("name", f"Display {m['id']}"), m["id"])
        self._monitor_combo.blockSignals(False)

    @pyqtSlot(str)
    def _on_clipboard(self, text: str) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage(f"Clipboard received ({len(text)} chars)", 2000)

    @pyqtSlot(str)
    def _on_status(self, text: str) -> None:
        self.statusBar().showMessage(text, 3000)

    @pyqtSlot(str)
    def _on_file_status(self, msg: str) -> None:
        self.statusBar().showMessage(msg, 5000)

    @pyqtSlot(float)
    def _on_fps(self, fps: float) -> None:
        self._lbl_fps.setText(f"{fps:.0f} fps")

    def _on_monitor_selected(self, index: int) -> None:
        monitor_id = self._monitor_combo.itemData(index)
        if monitor_id is not None:
            self._worker.send_input({
                "type": MessageType.MONITOR_SELECT.value,
                "monitor_id": monitor_id,
            })
            name = self._monitor_combo.currentText()
            self._lbl_monitor.setText(name)

    # ── Actions ────────────────────────────────────────────────────────────

    def _show_connect_dialog(self) -> None:
        dlg = ConnectDialog(self._cfg, self)
        if dlg.exec():
            dlg.apply_to_config()
            self._worker.configure(self._cfg)
            self._worker.start()         # starts the QThread
            self._worker.start_connection()

    def _show_settings(self) -> None:
        dlg = SettingsDialog(self._cfg, self)
        dlg.exec()

    def _pick_and_send_file(self) -> None:
        import shutil
        from pathlib import Path
        path, _ = QFileDialog.getOpenFileName(self, "Send File to Agent")
        if not path:
            return
        watch_dir = Path(self._cfg.files.send_watch_dir).expanduser()
        watch_dir.mkdir(parents=True, exist_ok=True)
        dest = watch_dir / Path(path).name
        shutil.copy2(path, dest)
        self.statusBar().showMessage(f"Queued: {Path(path).name}", 3000)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _set_connected(self, on: bool) -> None:
        self._connected = on
        self._act_connect.setEnabled(not on)
        self._act_disconnect.setEnabled(on)
        self._act_pull_clip.setEnabled(on)
        self._act_push_clip.setEnabled(on)
        self._act_send_file.setEnabled(on)
        self._monitor_combo.setEnabled(on)

    # ── Keyboard shortcuts ─────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        mods = event.modifiers()
        ctrl  = bool(mods & Qt.KeyboardModifier.ControlModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        key   = event.key()

        if ctrl and shift and key == Qt.Key.Key_C:
            self._worker.pull_clipboard()
            return
        if ctrl and shift and key == Qt.Key.Key_V:
            self._worker.push_clipboard()
            return

        # Pass everything else to the screen widget (which has focus normally,
        # but just in case focus lands on the window)
        self._screen.keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self._worker.stop_connection()
        self._worker.wait(2000)
        event.accept()
