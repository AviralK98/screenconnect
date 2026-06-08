from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pyperclip

from ...core.feature import FeatureHandler
from ...core.protocol import Message, MessageType

if TYPE_CHECKING:
    from ...core.session import Session
    from ...core.transport import Connection

log = logging.getLogger(__name__)


class ClipboardFeature(FeatureHandler):
    handles = frozenset({MessageType.CLIPBOARD_REQUEST, MessageType.CLIPBOARD_DATA})

    async def pull_clipboard(self, transport: "Connection") -> None:
        """Request the agent's clipboard → paste locally when received."""
        await transport.send_message(Message(MessageType.CLIPBOARD_REQUEST, {}))

    async def push_clipboard(self, transport: "Connection") -> None:
        """Push local clipboard content to the agent."""
        try:
            content = pyperclip.paste()
            await transport.send_message(Message(
                MessageType.CLIPBOARD_DATA,
                {"content": content, "mime": "text/plain"},
            ))
            log.debug("Pushed clipboard to agent (%d chars)", len(content))
        except Exception as e:
            log.warning("Clipboard read failed: %s", e)

    async def handle(self, session: "Session", transport: "Connection", msg) -> None:
        if msg.type == MessageType.CLIPBOARD_REQUEST:
            await self.push_clipboard(transport)

        elif msg.type == MessageType.CLIPBOARD_DATA:
            content = msg.payload.get("content", "")
            try:
                pyperclip.copy(content)
                log.info("Clipboard updated from agent (%d chars)", len(content))
            except Exception as e:
                log.warning("Clipboard write failed: %s", e)
