"""Viewer preferences dialog (tabbed)."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSlider, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)
from PyQt6.QtCore import Qt

from ..core.config import Config


class SettingsDialog(QDialog):
    def __init__(self, cfg: Config, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Viewer Settings")
        self.setMinimumWidth(440)
        self._cfg = cfg
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        tabs.addTab(self._reconnect_tab(), "Reconnect")
        tabs.addTab(self._tls_tab(), "TLS")
        tabs.addTab(self._files_tab(), "Files")

        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ── Tabs ──────────────────────────────────────────────────────────────

    def _reconnect_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self._rc_enabled = QCheckBox("Auto-reconnect on disconnect")
        form.addRow(self._rc_enabled)

        self._rc_max = QSpinBox()
        self._rc_max.setRange(0, 9999)
        self._rc_max.setSpecialValueText("Unlimited")
        form.addRow("Max attempts:", self._rc_max)

        self._rc_init = QDoubleSpinBox()
        self._rc_init.setRange(0.1, 60.0)
        self._rc_init.setSuffix(" s")
        form.addRow("Initial delay:", self._rc_init)

        self._rc_max_delay = QDoubleSpinBox()
        self._rc_max_delay.setRange(1.0, 300.0)
        self._rc_max_delay.setSuffix(" s")
        form.addRow("Max delay:", self._rc_max_delay)

        self._rc_factor = QDoubleSpinBox()
        self._rc_factor.setRange(1.0, 10.0)
        self._rc_factor.setSingleStep(0.5)
        form.addRow("Backoff factor:", self._rc_factor)
        return w

    def _tls_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self._tls_enabled = QCheckBox("Enable TLS (wss://)")
        form.addRow(self._tls_enabled)

        self._tls_ca = QLineEdit()
        self._tls_ca.setPlaceholderText("certs/ca.crt  (leave blank to use fingerprint)")
        form.addRow("CA file:", self._tls_ca)

        self._tls_fp = QLineEdit()
        self._tls_fp.setPlaceholderText("SHA-256 hex fingerprint from agent")
        form.addRow("Fingerprint:", self._tls_fp)

        self._tls_enabled.toggled.connect(lambda on: [
            self._tls_ca.setEnabled(on), self._tls_fp.setEnabled(on),
        ])
        return w

    def _files_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self._files_watch = QLineEdit()
        self._files_watch.setPlaceholderText("~/Desktop/sc_send")
        form.addRow("Watch dir (outgoing):", self._files_watch)
        return w

    # ── Load / save ───────────────────────────────────────────────────────

    def _load(self) -> None:
        rc = self._cfg.reconnect
        self._rc_enabled.setChecked(rc.enabled)
        self._rc_max.setValue(rc.max_attempts)
        self._rc_init.setValue(rc.initial_delay)
        self._rc_max_delay.setValue(rc.max_delay)
        self._rc_factor.setValue(rc.backoff_factor)

        tls = self._cfg.tls
        self._tls_enabled.setChecked(tls.enabled)
        self._tls_ca.setText(tls.ca_file)
        self._tls_fp.setText(tls.fingerprint)
        self._tls_ca.setEnabled(tls.enabled)
        self._tls_fp.setEnabled(tls.enabled)

        self._files_watch.setText(self._cfg.files.send_watch_dir)

    def _save_and_accept(self) -> None:
        rc = self._cfg.reconnect
        rc.enabled       = self._rc_enabled.isChecked()
        rc.max_attempts  = self._rc_max.value()
        rc.initial_delay = self._rc_init.value()
        rc.max_delay     = self._rc_max_delay.value()
        rc.backoff_factor = self._rc_factor.value()

        tls = self._cfg.tls
        tls.enabled     = self._tls_enabled.isChecked()
        tls.ca_file     = self._tls_ca.text().strip()
        tls.fingerprint = self._tls_fp.text().strip()

        self._cfg.files.send_watch_dir = self._files_watch.text().strip()
        self.accept()
