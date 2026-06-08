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

    async def handle(self, session: "Session", transport: "Connection", msg) -> None:
        if msg.type == MessageType.CLIPBOARD_REQUEST:
            try:
                content = pyperclip.paste()
                await transport.send_message(Message(
                    MessageType.CLIPBOARD_DATA,
                    {"content": content, "mime": "text/plain"},
                ))
                log.debug("Sent clipboard to viewer (%d chars)", len(content))
            except Exception as e:
                log.warning("Clipboard read failed: %s", e)

        elif msg.type == MessageType.CLIPBOARD_DATA:
            content = msg.payload.get("content", "")
            try:
                pyperclip.copy(content)
                log.debug("Set clipboard from viewer (%d chars)", len(content))
            except Exception as e:
                log.warning("Clipboard write failed: %s", e)
