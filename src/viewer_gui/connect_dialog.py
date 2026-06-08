"""Connection dialog shown on launch or when disconnected."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QRadioButton, QSpinBox,
    QVBoxLayout, QWidget,
)

from ..core.config import Config


class ConnectDialog(QDialog):
    def __init__(self, cfg: Config, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Connect to Agent")
        self.setMinimumWidth(380)
        self._cfg = cfg
        self._build_ui()
        self._load_from_config()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Server ──────────────────────────────────────────────────────
        server_box = QGroupBox("Agent")
        form = QFormLayout(server_box)

        self._host = QLineEdit()
        self._host.setPlaceholderText("192.168.1.50")
        form.addRow("Host / IP:", self._host)

        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(8765)
        form.addRow("Port:", self._port)

        layout.addWidget(server_box)

        # ── Auth ────────────────────────────────────────────────────────
        auth_box = QGroupBox("Authentication")
        auth_layout = QVBoxLayout(auth_box)

        mode_row = QHBoxLayout()
        self._rb_token = QRadioButton("Token")
        self._rb_user  = QRadioButton("Username / Password")
        self._rb_token.setChecked(True)
        mode_row.addWidget(self._rb_token)
        mode_row.addWidget(self._rb_user)
        auth_layout.addLayout(mode_row)

        cred_form = QFormLayout()
        self._token    = QLineEdit()
        self._username = QLineEdit()
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)

        cred_form.addRow("Token:", self._token)
        cred_form.addRow("Username:", self._username)
        cred_form.addRow("Password:", self._password)
        auth_layout.addLayout(cred_form)
        layout.addWidget(auth_box)

        self._rb_token.toggled.connect(self._update_auth_fields)
        self._update_auth_fields()

        # ── Buttons ──────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Connect")
        layout.addWidget(buttons)

    def _update_auth_fields(self) -> None:
        token_mode = self._rb_token.isChecked()
        self._token.setEnabled(token_mode)
        self._username.setEnabled(not token_mode)
        self._password.setEnabled(not token_mode)

    def _load_from_config(self) -> None:
        self._host.setText(self._cfg.server.host)
        self._port.setValue(self._cfg.server.port)
        if self._cfg.auth.mode == "users":
            self._rb_user.setChecked(True)
            self._username.setText(self._cfg.auth.username)
        else:
            self._rb_token.setChecked(True)
            self._token.setText(self._cfg.auth.token)

    def apply_to_config(self) -> None:
        """Write dialog values back into the Config object."""
        self._cfg.server.host = self._host.text().strip()
        self._cfg.server.port = self._port.value()
        if self._rb_user.isChecked():
            self._cfg.auth.mode     = "users"
            self._cfg.auth.username = self._username.text().strip()
            self._cfg.auth.password = self._password.text()
        else:
            self._cfg.auth.mode  = "token"
            self._cfg.auth.token = self._token.text().strip()
