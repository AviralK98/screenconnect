from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8765


@dataclass
class TLSConfig:
    enabled: bool = False
    cert_file: str = "certs/agent.crt"
    key_file: str = "certs/agent.key"
    ca_file: str = ""
    fingerprint: str = ""


@dataclass
class AuthConfig:
    mode: str = "token"       # "token" | "users"
    token: str = "change-this-token"
    username: str = ""
    password: str = ""


@dataclass
class ScreenConfig:
    fps: int = 12
    jpeg_quality: int = 55
    monitor_index: int = 0


@dataclass
class FilesConfig:
    drop_dir: str = "~/Downloads/screenconnect"
    send_watch_dir: str = "~/Desktop/sc_send"


@dataclass
class ReconnectConfig:
    enabled: bool = True
    max_attempts: int = 0     # 0 = infinite
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0


@dataclass
class LoggingConfig:
    level: str = "INFO"


@dataclass
class Config:
    server: ServerConfig = field(default_factory=ServerConfig)
    tls: TLSConfig = field(default_factory=TLSConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    screen: ScreenConfig = field(default_factory=ScreenConfig)
    files: FilesConfig = field(default_factory=FilesConfig)
    reconnect: ReconnectConfig = field(default_factory=ReconnectConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        path = Path(path)
        raw: dict = {}
        if path.exists():
            with open(path, "rb") as f:
                raw = tomllib.load(f)

        cfg = cls(
            server=ServerConfig(**{**ServerConfig.__dataclass_fields__, **raw.get("server", {})}),
            tls=TLSConfig(**{k: v for k, v in {**vars(TLSConfig()), **raw.get("tls", {})}.items() if k in TLSConfig.__dataclass_fields__}),
            auth=AuthConfig(**{k: v for k, v in {**vars(AuthConfig()), **raw.get("auth", {})}.items() if k in AuthConfig.__dataclass_fields__}),
            screen=ScreenConfig(**{k: v for k, v in {**vars(ScreenConfig()), **raw.get("screen", {})}.items() if k in ScreenConfig.__dataclass_fields__}),
            files=FilesConfig(**{k: v for k, v in {**vars(FilesConfig()), **raw.get("files", {})}.items() if k in FilesConfig.__dataclass_fields__}),
            reconnect=ReconnectConfig(**{k: v for k, v in {**vars(ReconnectConfig()), **raw.get("reconnect", {})}.items() if k in ReconnectConfig.__dataclass_fields__}),
            logging=LoggingConfig(**{k: v for k, v in {**vars(LoggingConfig()), **raw.get("logging", {})}.items() if k in LoggingConfig.__dataclass_fields__}),
        )

        _apply_env_overrides(cfg)
        return cfg

    @classmethod
    def defaults(cls) -> "Config":
        return cls()


_SECTION_MAP = {
    "server": "server",
    "tls": "tls",
    "auth": "auth",
    "screen": "screen",
    "files": "files",
    "reconnect": "reconnect",
    "logging": "logging",
}


def _apply_env_overrides(cfg: Config) -> None:
    prefix = "SC_"
    for env_key, env_val in os.environ.items():
        if not env_key.startswith(prefix):
            continue
        parts = env_key[len(prefix):].lower().split("_", 1)
        if len(parts) != 2:
            continue
        section_name, field_name = parts
        if section_name not in _SECTION_MAP:
            continue
        section = getattr(cfg, _SECTION_MAP[section_name], None)
        if section is None or not hasattr(section, field_name):
            continue
        current = getattr(section, field_name)
        try:
            if isinstance(current, bool):
                setattr(section, field_name, env_val.lower() in ("1", "true", "yes"))
            elif isinstance(current, int):
                setattr(section, field_name, int(env_val))
            elif isinstance(current, float):
                setattr(section, field_name, float(env_val))
            else:
                setattr(section, field_name, env_val)
        except (ValueError, TypeError):
            pass
