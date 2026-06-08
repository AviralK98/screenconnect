from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional

import websockets
import websockets.exceptions

from ..core.auth import Authenticator
from ..core.config import Config
from ..core.feature import FeatureRegistry
from ..core.session import Session
from ..core.transport import Connection, build_server_ssl_context
from ..core.crypto import generate_self_signed

log = logging.getLogger(__name__)


class AgentServer:
    def __init__(
        self,
        cfg: Config,
        registry: FeatureRegistry,
        auth: Authenticator,
        on_client_connect: Optional[Callable[[str, str], None]] = None,
        on_client_disconnect: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._cfg = cfg
        self._registry = registry
        self._auth = auth
        self._on_client_connect = on_client_connect
        self._on_client_disconnect = on_client_disconnect

    async def run(self) -> None:
        ssl_ctx = self._build_ssl()
        host = self._cfg.server.host
        port = self._cfg.server.port
        scheme = "wss" if self._cfg.tls.enabled else "ws"
        log.info("Agent listening on %s://%s:%d", scheme, host, port)

        async with websockets.serve(
            self._handle_connection,
            host,
            port,
            ssl=ssl_ctx,
            max_size=None,
            ping_interval=20,
            ping_timeout=20,
        ):
            await asyncio.Future()

    async def _handle_connection(self, ws: websockets.WebSocketServerProtocol) -> None:
        conn = Connection(ws)
        log.info("Incoming connection from %s", conn.remote_address)

        result = await self._auth.challenge(conn)
        if not result.success:
            log.warning("Auth failed from %s: %s", conn.remote_address, result.reason)
            await conn.close()
            return

        session = Session(user=result.user)
        user_label = result.user.name if result.user else "token"
        log.info("Session started for user=%s from %s", user_label, conn.remote_address)

        if self._on_client_connect:
            self._on_client_connect(conn.remote_address, user_label)

        await self._registry.broadcast_connect(session, conn)
        try:
            while True:
                msg = await conn.recv()
                await self._registry.dispatch(session, conn, msg)
        except websockets.exceptions.ConnectionClosed:
            log.info("Client disconnected: %s", conn.remote_address)
        except Exception:
            log.exception("Unexpected error in session from %s", conn.remote_address)
        finally:
            await self._registry.broadcast_disconnect(session)
            if self._on_client_disconnect:
                self._on_client_disconnect(conn.remote_address)

    def _build_ssl(self):
        cfg = self._cfg.tls
        if not cfg.enabled:
            return None
        cert = Path(cfg.cert_file)
        key = Path(cfg.key_file)
        if not cert.exists() or not key.exists():
            log.info("TLS cert not found — generating self-signed cert")
            fp = generate_self_signed(cert, key)
            log.info("Cert fingerprint (paste into viewer config): %s", fp)
        return build_server_ssl_context(cfg)
