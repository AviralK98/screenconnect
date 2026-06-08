from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ...core.feature import FeatureHandler
from ...core.protocol import (
    BinaryFrame, BinaryMessageType, Message, MessageType,
    unpack_file_chunk,
)

if TYPE_CHECKING:
    from ...core.config import Config
    from ...core.session import Session
    from ...core.transport import Connection

log = logging.getLogger(__name__)


@dataclass
class _IncomingTransfer:
    transfer_id: str
    filename: str
    expected_size: int
    tmp_path: Path
    tmp_file: object        # open file handle
    hasher: object = field(default_factory=hashlib.sha256)
    bytes_received: int = 0


class FileTransferFeature(FeatureHandler):
    handles = frozenset({
        MessageType.FILE_START,
        MessageType.FILE_END,
        MessageType.FILE_REJECT,
    })
    handles_binary = True

    def __init__(self, cfg: "Config") -> None:
        self._drop_dir = Path(cfg.files.drop_dir).expanduser()

    async def on_connect(self, session: "Session", transport: "Connection") -> None:
        self._drop_dir.mkdir(parents=True, exist_ok=True)

    async def handle(self, session: "Session", transport: "Connection", msg) -> None:
        if isinstance(msg, BinaryFrame):
            if msg.type == BinaryMessageType.FILE_CHUNK:
                await self._handle_chunk(session, msg.data)
            return

        if msg.type == MessageType.FILE_START:
            await self._handle_file_start(session, transport, msg)
        elif msg.type == MessageType.FILE_END:
            await self._handle_file_end(session, transport, msg)
        elif msg.type == MessageType.FILE_REJECT:
            tid = msg.payload.get("transfer_id", "")
            self._cleanup_transfer(session, tid)

    async def _handle_file_start(
        self, session: "Session", transport: "Connection", msg
    ) -> None:
        tid = msg.payload.get("transfer_id", "")
        filename = Path(msg.payload.get("filename", "file")).name  # strip any path traversal
        size = int(msg.payload.get("size", 0))

        tmp_fd, tmp_path = tempfile.mkstemp(dir=self._drop_dir, prefix=".tmp_")
        tmp_file = os.fdopen(tmp_fd, "wb")

        session.transfer_registry[tid] = _IncomingTransfer(
            transfer_id=tid,
            filename=filename,
            expected_size=size,
            tmp_path=Path(tmp_path),
            tmp_file=tmp_file,
        )
        await transport.send_message(Message(MessageType.FILE_ACCEPT, {"transfer_id": tid}))
        log.info("Receiving file '%s' (%d bytes) — transfer %s", filename, size, tid[:8])

    async def _handle_chunk(self, session: "Session", data: bytes) -> None:
        tid, chunk_index, chunk_data = unpack_file_chunk(data)
        transfer: _IncomingTransfer | None = session.transfer_registry.get(tid)
        if transfer is None:
            log.warning("FILE_CHUNK for unknown transfer %s", tid[:8])
            return
        transfer.tmp_file.write(chunk_data)
        transfer.hasher.update(chunk_data)
        transfer.bytes_received += len(chunk_data)

    async def _handle_file_end(
        self, session: "Session", transport: "Connection", msg
    ) -> None:
        tid = msg.payload.get("transfer_id", "")
        expected_checksum = msg.payload.get("checksum", "")
        transfer: _IncomingTransfer | None = session.transfer_registry.pop(tid, None)
        if transfer is None:
            return

        transfer.tmp_file.close()
        actual = transfer.hasher.hexdigest()

        if actual != expected_checksum:
            transfer.tmp_path.unlink(missing_ok=True)
            await transport.send_message(Message(
                MessageType.FILE_ERROR,
                {"transfer_id": tid, "reason": "checksum mismatch"},
            ))
            log.error("File transfer %s failed: checksum mismatch", tid[:8])
            return

        dest = self._drop_dir / transfer.filename
        # Avoid collisions
        stem, suffix = dest.stem, dest.suffix
        counter = 1
        while dest.exists():
            dest = self._drop_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        os.replace(transfer.tmp_path, dest)
        log.info("Received file '%s' → %s", transfer.filename, dest)

    def _cleanup_transfer(self, session: "Session", tid: str) -> None:
        transfer: _IncomingTransfer | None = session.transfer_registry.pop(tid, None)
        if transfer:
            transfer.tmp_file.close()
            transfer.tmp_path.unlink(missing_ok=True)
