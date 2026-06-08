from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from ...core.feature import FeatureHandler
from ...core.protocol import (
    Message, MessageType,
    pack_file_chunk,
)

if TYPE_CHECKING:
    from ...core.config import Config
    from ...core.session import Session
    from ...core.transport import Connection

log = logging.getLogger(__name__)

CHUNK_SIZE = 65536   # 64 KB


class FileTransferFeature(FeatureHandler):
    handles = frozenset({
        MessageType.FILE_ACCEPT,
        MessageType.FILE_REJECT,
        MessageType.FILE_ERROR,
    })

    def __init__(self, cfg: "Config") -> None:
        self._watch_dir = Path(cfg.files.send_watch_dir).expanduser()
        self._transport: "Connection | None" = None
        self._session: "Session | None" = None
        self._seen: set[Path] = set()
        self._task: asyncio.Task | None = None

    async def on_connect(self, session: "Session", transport: "Connection") -> None:
        self._transport = transport
        self._session = session
        self._watch_dir.mkdir(parents=True, exist_ok=True)
        # Seed seen set so pre-existing files aren't immediately sent
        self._seen = set(self._watch_dir.glob("*"))
        self._task = asyncio.create_task(self._watch_loop(), name="file_watch")

    async def on_disconnect(self, session: "Session") -> None:
        if self._task:
            self._task.cancel()
            self._task = None
        self._transport = None

    async def handle(self, session: "Session", transport: "Connection", msg) -> None:
        if msg.type == MessageType.FILE_ACCEPT:
            log.info("File transfer accepted: %s", msg.payload.get("transfer_id", "")[:8])
        elif msg.type == MessageType.FILE_REJECT:
            log.warning("File transfer rejected: %s — %s",
                        msg.payload.get("transfer_id", "")[:8],
                        msg.payload.get("reason", ""))
        elif msg.type == MessageType.FILE_ERROR:
            log.error("File transfer error: %s — %s",
                      msg.payload.get("transfer_id", "")[:8],
                      msg.payload.get("reason", ""))

    # ------------------------------------------------------------------ #
    # Watch loop                                                           #
    # ------------------------------------------------------------------ #

    async def _watch_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(1.0)
                if self._transport is None:
                    break
                current = set(self._watch_dir.glob("*"))
                new_files = current - self._seen
                self._seen = current
                for path in sorted(new_files):
                    if path.is_file():
                        asyncio.create_task(
                            self._send_file(path),
                            name=f"send_{path.name}",
                        )
        except asyncio.CancelledError:
            pass

    async def _send_file(self, path: Path) -> None:
        transport = self._transport
        if transport is None:
            return

        tid = str(uuid.uuid4())
        size = path.stat().st_size
        log.info("Sending file '%s' (%d bytes) → transfer %s", path.name, size, tid[:8])

        await transport.send_message(Message(
            MessageType.FILE_START,
            {
                "transfer_id": tid,
                "filename": path.name,
                "size": size,
            },
        ))

        hasher = hashlib.sha256()
        chunk_index = 0
        try:
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    payload = pack_file_chunk(tid, chunk_index, chunk)
                    await transport.send_binary(payload)
                    chunk_index += 1
                    await asyncio.sleep(0)   # yield to event loop
        except Exception as e:
            log.error("Error reading '%s': %s", path.name, e)
            return

        await transport.send_message(Message(
            MessageType.FILE_END,
            {"transfer_id": tid, "checksum": hasher.hexdigest()},
        ))
        log.info("File '%s' sent (%d chunks)", path.name, chunk_index)
