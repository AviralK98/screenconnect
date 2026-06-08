from __future__ import annotations

import asyncio
import logging

import websockets
import websockets.exceptions

from ..core.auth import Authenticator
from ..core.config import Config
from ..core.feature import FeatureRegistry
from ..core.protocol import Message, MessageType
from ..core.session import Session
from ..core.transport import Connection, build_client_ssl_context, verify_fingerprint

log = logging.getLogger(__name__)


class ViewerClient:
    def __init__(
        self,
        cfg: Config,
        registry: FeatureRegistry,
        auth: Authenticator,
    ) -> None:
        self._cfg = cfg
        self._registry = registry
        self._auth = auth

    def _uri(self) -> str:
        scheme = "wss" if self._cfg.tls.enabled else "ws"
        return f"{scheme}://{self._cfg.server.host}:{self._cfg.server.port}"

    async def run(self) -> None:
        rcfg = self._cfg.reconnect
        attempt = 0
        delay = rcfg.initial_delay

        while True:
            attempt += 1
            if rcfg.max_attempts > 0 and attempt > rcfg.max_attempts:
                log.error("Max reconnect attempts (%d) reached — giving up", rcfg.max_attempts)
                return

            try:
                await self._connect_once(attempt)
                # Clean disconnect — reset back-off
                attempt = 0
                delay = rcfg.initial_delay
            except (websockets.exceptions.ConnectionClosed,
                    websockets.exceptions.WebSocketException,
                    OSError) as exc:
                log.warning("Connection lost: %s", exc)

            if not rcfg.enabled:
                log.info("Reconnect disabled — exiting")
                return

            status = f"Reconnecting… attempt {attempt}"
            if rcfg.max_attempts > 0:
                status += f"/{rcfg.max_attempts}"
            log.info("%s (waiting %.1fs)", status, delay)

            # Push status into a synthetic message for DisplayFeature to show
            await self._registry.dispatch(
                Session(),
                _NullTransport(),
                Message(MessageType.DISPLAY_STATUS, {"text": status}),
            )

            await asyncio.sleep(delay)
            delay = min(delay * rcfg.backoff_factor, rcfg.max_delay)

    async def _connect_once(self, attempt: int) -> None:
        uri = self._uri()
        ssl_ctx = build_client_ssl_context(self._cfg.tls)
        log.info("Connecting to %s (attempt %d)", uri, attempt)

        async with websockets.connect(
            uri,
            ssl=ssl_ctx,
            max_size=None,
            ping_interval=20,
            ping_timeout=20,
        ) as ws:
            if self._cfg.tls.enabled and self._cfg.tls.fingerprint:
                if not verify_fingerprint(ws, self._cfg.tls.fingerprint):
                    log.error("TLS fingerprint mismatch — closing connection")
                    await ws.close()
                    return

            conn = Connection(ws)
            result = await self._auth.respond(conn)
            if not result.success:
                log.error("Auth failed: %s", result.reason)
                return

            session = Session(user=result.user)
            log.info("Connected and authenticated")

            await self._registry.broadcast_connect(session, conn)
            try:
                while True:
                    msg = await conn.recv()
                    await self._registry.dispatch(session, conn, msg)
            except websockets.exceptions.ConnectionClosed:
                raise
            finally:
                await self._registry.broadcast_disconnect(session)


class _NullTransport:
    """Placeholder transport used when pushing synthetic messages with no live connection."""
    async def send_message(self, msg): pass
    async def send_binary(self, data): pass
