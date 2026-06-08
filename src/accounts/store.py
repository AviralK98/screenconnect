from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import bcrypt


@dataclass
class User:
    id: str
    name: str
    password_hash: str
    created_at: str


class UserStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, dict]:
        if not self._path.exists():
            return {}
        with open(self._path) as f:
            return json.load(f)

    def _save(self, data: dict[str, dict]) -> None:
        tmp = self._path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self._path)

    def add(self, name: str, password: str) -> User:
        data = self._load()
        if name in data:
            raise ValueError(f"User '{name}' already exists")
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User(
            id=str(uuid.uuid4()),
            name=name,
            password_hash=pw_hash,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        data[name] = asdict(user)
        self._save(data)
        return user

    def remove(self, name: str) -> None:
        data = self._load()
        if name not in data:
            raise KeyError(f"User '{name}' not found")
        del data[name]
        self._save(data)

    def set_password(self, name: str, password: str) -> None:
        data = self._load()
        if name not in data:
            raise KeyError(f"User '{name}' not found")
        data[name]["password_hash"] = bcrypt.hashpw(
            password.encode(), bcrypt.gensalt()
        ).decode()
        self._save(data)

    def verify(self, name: str, password: str) -> User | None:
        data = self._load()
        entry = data.get(name)
        if entry is None:
            return None
        if bcrypt.checkpw(password.encode(), entry["password_hash"].encode()):
            return User(**entry)
        return None

    def list_users(self) -> list[User]:
        return [User(**v) for v in self._load().values()]
