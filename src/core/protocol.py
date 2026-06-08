from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from enum import IntEnum, Enum


class MessageType(str, Enum):
    # Auth
    AUTH             = "auth"
    AUTH_OK          = "auth_ok"
    AUTH_FAIL        = "auth_fail"

    # Screen / monitor
    MONITOR_LIST     = "monitor_list"
    MONITOR_SELECT   = "monitor_select"

    # Input
    MOUSE_MOVE       = "mouse_move"
    MOUSE_CLICK      = "mouse_click"
    MOUSE_SCROLL     = "mouse_scroll"
    KEY              = "key"

    # Clipboard
    CLIPBOARD_REQUEST = "clipboard_request"
    CLIPBOARD_DATA    = "clipboard_data"

    # File transfer
    FILE_START       = "file_start"
    FILE_END         = "file_end"
    FILE_ACCEPT      = "file_accept"
    FILE_REJECT      = "file_reject"
    FILE_ERROR       = "file_error"

    # Housekeeping
    PING             = "ping"
    PONG             = "pong"

    # Internal display signal (never sent over the wire)
    DISPLAY_STATUS   = "display_status"


class BinaryMessageType(IntEnum):
    FRAME      = 0x01
    FILE_CHUNK = 0x02


@dataclass
class Message:
    type: MessageType
    payload: dict

    @classmethod
    def from_text(cls, raw: str) -> "Message":
        data = json.loads(raw)
        msg_type = MessageType(data.pop("type"))
        return cls(type=msg_type, payload=data)

    def to_text(self) -> str:
        return json.dumps({"type": self.type.value, **self.payload})


@dataclass
class BinaryFrame:
    type: BinaryMessageType
    data: bytes


# FILE_CHUNK binary layout:
#   1 byte  : BinaryMessageType
#   36 bytes: transfer_id (ASCII UUID4)
#   4 bytes : chunk_index (uint32 big-endian)
#   N bytes : chunk data

_FILE_CHUNK_HEADER = struct.Struct("!36sI")   # 36-char id + uint32


def pack_binary(btype: BinaryMessageType, data: bytes) -> bytes:
    return bytes([btype]) + data


def unpack_binary(raw: bytes) -> BinaryFrame:
    btype = BinaryMessageType(raw[0])
    return BinaryFrame(type=btype, data=raw[1:])


def pack_file_chunk(transfer_id: str, chunk_index: int, chunk_data: bytes) -> bytes:
    header = _FILE_CHUNK_HEADER.pack(
        transfer_id.encode("ascii"),
        chunk_index,
    )
    return bytes([BinaryMessageType.FILE_CHUNK]) + header + chunk_data


def unpack_file_chunk(data: bytes) -> tuple[str, int, bytes]:
    """Returns (transfer_id, chunk_index, chunk_data). Call after stripping type byte."""
    header_size = _FILE_CHUNK_HEADER.size
    tid_bytes, chunk_index = _FILE_CHUNK_HEADER.unpack(data[:header_size])
    transfer_id = tid_bytes.decode("ascii")
    return transfer_id, chunk_index, data[header_size:]
