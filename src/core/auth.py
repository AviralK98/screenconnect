from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .protocol import Message, MessageType
from .session import User

if TYPE_CHECKING:
    from .transport import Connection
    from .config import AuthConfig

log = logging.getLogger(__name__)


@dataclass
class AuthResult:
    success: bool
    user: User | None = None
    reason: str | None = None


class Authenticator(ABC):
    @abstractmethod
    async def challenge(self, transport: "Connection") -> AuthResult:
        """Server side: read the auth message from client, validate, send result."""

    @abstractmethod
    async def respond(self, transport: "Connection") -> AuthResult:
        """Client side: send credentials, read server response."""


class TokenAuthenticator(Authenticator):
    def __init__(self, token: str) -> None:
        self._token = token

    async def challenge(self, transport: "Connection") -> AuthResult:
        msg = await transport.recv()
        if not isinstance(msg, Message) or msg.type != MessageType.AUTH:
            await transport.send_message(
                Message(MessageType.AUTH_FAIL, {"reason": "expected auth message"})
            )
            return AuthResult(success=False, reason="expected auth message")

        if msg.payload.get("token") != self._token:
            await transport.send_message(
                Message(MessageType.AUTH_FAIL, {"reason": "invalid token"})
            )
            return AuthResult(success=False, reason="invalid token")

        await transport.send_message(Message(MessageType.AUTH_OK, {}))
        log.info("Token auth succeeded")
        return AuthResult(success=True)

    async def respond(self, transport: "Connection") -> AuthResult:
        await transport.send_message(
            Message(MessageType.AUTH, {"token": self._token})
        )
        msg = await transport.recv()
        if not isinstance(msg, Message):
            return AuthResult(success=False, reason="unexpected binary frame during auth")

        if msg.type == MessageType.AUTH_OK:
            return AuthResult(success=True, user=msg.payload.get("user"))
        reason = msg.payload.get("reason", "auth failed")
        return AuthResult(success=False, reason=reason)


class UserAccountAuthenticator(Authenticator):
    def __init__(self, store: "UserStore", username: str = "", password: str = "") -> None:  # noqa: F821
        self._store = store
        self._username = username
        self._password = password

    async def challenge(self, transport: "Connection") -> AuthResult:
        msg = await transport.recv()
        if not isinstance(msg, Message) or msg.type != MessageType.AUTH:
            await transport.send_message(
                Message(MessageType.AUTH_FAIL, {"reason": "expected auth message"})
            )
            return AuthResult(success=False, reason="expected auth message")

        username = msg.payload.get("username", "")
        password = msg.payload.get("password", "")
        user = self._store.verify(username, password)

        if user is None:
            await transport.send_message(
                Message(MessageType.AUTH_FAIL, {"reason": "invalid credentials"})
            )
            return AuthResult(success=False, reason="invalid credentials")

        await transport.send_message(
            Message(MessageType.AUTH_OK, {"user": {"id": user.id, "name": user.name}})
        )
        log.info("User '%s' authenticated", username)
        return AuthResult(success=True, user=user)

    async def respond(self, transport: "Connection") -> AuthResult:
        await transport.send_message(
            Message(MessageType.AUTH, {
                "username": self._username,
                "password": self._password,
            })
        )
        msg = await transport.recv()
        if not isinstance(msg, Message):
            return AuthResult(success=False, reason="unexpected binary frame during auth")

        if msg.type == MessageType.AUTH_OK:
            raw_user = msg.payload.get("user")
            user = User(id=raw_user["id"], name=raw_user["name"]) if raw_user else None
            return AuthResult(success=True, user=user)
        return AuthResult(success=False, reason=msg.payload.get("reason", "auth failed"))
