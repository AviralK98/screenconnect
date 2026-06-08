from __future__ import annotations

import logging
import ssl
from pathlib import Path
from typing import TYPE_CHECKING

import websockets
import websockets.exceptions

from .protocol import Message, BinaryFrame, unpack_binary

if TYPE_CHECKING:
    from .config import TLSConfig

log = logging.getLogger(__name__)


class Connection:
    """Wraps a live websockets connection. Send/receive typed messages."""

    def __init__(self, ws: websockets.WebSocketCommonProtocol) -> None:
        self._ws = ws

    async def send_message(self, msg: Message) -> None:
        await self._ws.send(msg.to_text())

    async def send_binary(self, data: bytes) -> None:
        await self._ws.send(data)

    async def recv(self) -> Message | BinaryFrame:
        raw = await self._ws.recv()
        if isinstance(raw, bytes):
            return unpack_binary(raw)
        return Message.from_text(raw)

    async def close(self) -> None:
        await self._ws.close()

    @property
    def remote_address(self) -> str:
        addr = self._ws.remote_address
        return f"{addr[0]}:{addr[1]}" if addr else "unknown"


def build_server_ssl_context(cfg: "TLSConfig") -> ssl.SSLContext | None:
    if not cfg.enabled:
        return None
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=cfg.cert_file, keyfile=cfg.key_file)
    if cfg.ca_file:
        ctx.load_verify_locations(cfg.ca_file)
        ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


def build_client_ssl_context(cfg: "TLSConfig") -> ssl.SSLContext | None:
    if not cfg.enabled:
        return None
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    if cfg.ca_file:
        ctx.load_verify_locations(cfg.ca_file)
    else:
        # Trust system CAs but allow self-signed via fingerprint check
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def verify_fingerprint(ws: websockets.WebSocketClientProtocol, expected: str) -> bool:
    """Compare peer cert SHA-256 fingerprint (hex) against expected."""
    import hashlib
    ssl_obj = ws.transport.get_extra_info("ssl_object")
    if ssl_obj is None:
        return False
    der = ssl_obj.getpeercert(binary_form=True)
    actual = hashlib.sha256(der).hexdigest()
    return actual.lower() == expected.lower().replace(":", "")
