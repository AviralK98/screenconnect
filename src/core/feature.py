from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .protocol import MessageType, Message, BinaryFrame

if TYPE_CHECKING:
    from .session import Session
    from .transport import Connection

log = logging.getLogger(__name__)


class FeatureHandler(ABC):
    handles: frozenset[MessageType] = frozenset()
    handles_binary: bool = False

    async def on_connect(self, session: "Session", transport: "Connection") -> None:
        pass

    async def on_disconnect(self, session: "Session") -> None:
        pass

    async def handle(
        self,
        session: "Session",
        transport: "Connection",
        msg: Message | BinaryFrame,
    ) -> None:
        pass


class FeatureRegistry:
    def __init__(self) -> None:
        self._handlers: list[FeatureHandler] = []
        self._dispatch_map: dict[MessageType, FeatureHandler] = {}
        self._binary_handlers: list[FeatureHandler] = []

    def register(self, handler: FeatureHandler) -> None:
        self._handlers.append(handler)
        for msg_type in handler.handles:
            self._dispatch_map[msg_type] = handler
        if handler.handles_binary:
            self._binary_handlers.append(handler)

    async def dispatch(
        self,
        session: "Session",
        transport: "Connection",
        msg: Message | BinaryFrame,
    ) -> None:
        if isinstance(msg, BinaryFrame):
            for h in self._binary_handlers:
                try:
                    await h.handle(session, transport, msg)
                except Exception:
                    log.exception("Error in binary handler %s", h.__class__.__name__)
            return

        handler = self._dispatch_map.get(msg.type)
        if handler is None:
            log.debug("No handler for message type %s", msg.type)
            return
        try:
            await handler.handle(session, transport, msg)
        except Exception:
            log.exception("Error in handler %s for %s", handler.__class__.__name__, msg.type)

    async def broadcast_connect(
        self, session: "Session", transport: "Connection"
    ) -> None:
        for h in self._handlers:
            try:
                await h.on_connect(session, transport)
            except Exception:
                log.exception("Error in on_connect for %s", h.__class__.__name__)

    async def broadcast_disconnect(self, session: "Session") -> None:
        for h in self._handlers:
            try:
                await h.on_disconnect(session)
            except Exception:
                log.exception("Error in on_disconnect for %s", h.__class__.__name__)
