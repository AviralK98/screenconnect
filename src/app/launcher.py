"""Mode chooser shown when ScreenConnect launches.

A single app that can act as either side:
  • Agent  — share this machine's screen (be controlled)
  • Viewer — connect to and control another machine
"""
from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)


class _ModeCard(QFrame):
    """A clickable card describing one mode."""

    def __init__(self, emoji: str, title: str, desc: str, button_text: str,
                 on_click: Callable[[], None]) -> None:
        super().__init__()
        self.setObjectName("modeCard")
        self.setStyleSheet(
            "#modeCard { background:#1e1e1e; border:1px solid #3a3a3a; border-radius:14px; }"
            "#modeCard:hover { border-color:#4a7cc7; background:#212530; }"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(8)

        icon = QLabel(emoji)
        icon.setStyleSheet("font-size:34px;")
        lay.addWidget(icon)

        t = QLabel(title)
        t.setStyleSheet("font-size:16px; font-weight:bold; color:#f0f0f0;")
        lay.addWidget(t)

        d = QLabel(desc)
        d.setWordWrap(True)
        d.setStyleSheet("color:#999; font-size:12px;")
        lay.addWidget(d)
        lay.addStretch()

        btn = QPushButton(button_text)
        btn.clicked.connect(on_click)
        lay.addWidget(btn)


class LauncherWindow(QWidget):
    def __init__(self, open_agent: Callable[[], None],
                 open_viewer: Callable[[], None]) -> None:
        super().__init__()
        self.setWindowTitle("ScreenConnect")
        self.setMinimumWidth(560)

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 26)
        root.setSpacing(6)

        title = QLabel("ScreenConnect")
        title.setStyleSheet("font-size:24px; font-weight:bold;")
        root.addWidget(title)

        subtitle = QLabel("What would you like to do?")
        subtitle.setStyleSheet("color:#999; font-size:13px;")
        root.addWidget(subtitle)
        root.addSpacing(14)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        cards.addWidget(_ModeCard(
            "🖥️", "Share This Screen",
            "Let another device view and control this machine. "
            "Start the server and share its address.",
            "Start as Agent", open_agent,
        ))
        cards.addWidget(_ModeCard(
            "📡", "Control a Machine",
            "Connect to another device that is running the Agent "
            "and control it remotely.",
            "Open Viewer", open_viewer,
        ))
        root.addLayout(cards)

        hint = QLabel("You can open both at once — this machine can host and "
                      "control at the same time.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#777; font-size:11px; margin-top:14px;")
        root.addWidget(hint)
