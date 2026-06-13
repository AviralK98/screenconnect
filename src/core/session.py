from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Monitor:
    id: int
    x: int
    y: int
    width: int
    height: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "x": self.x, "y": self.y,
                "width": self.width, "height": self.height, "name": self.name}

    @classmethod
    def from_dict(cls, d: dict) -> "Monitor":
        return cls(**d)


@dataclass
class User:
    id: str
    name: str


@dataclass
class Session:
    user: User | None = None
    selected_monitor: int = 0
    monitors: list[Monitor] = field(default_factory=list)
    transfer_registry: dict[str, Any] = field(default_factory=dict)
    reconnect_status: str = ""
    # Frame scaling: native captured pixel size vs the size actually encoded
    # and sent. Used to map viewer click coords back to real screen pixels.
    frame_native: tuple[int, int] = (0, 0)
    frame_sent: tuple[int, int] = (0, 0)
