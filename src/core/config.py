from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def get_user_config_dir() -> Path:
    """Return platform-appropriate writable config directory.

    Used when running as a frozen app (PyInstaller).
    Development runs use the project's config/ folder instead.
    """
    if sys.platform == "darwin":
        d = Path.home() / "Library" / "Application Support" / "ScreenConnect"
    elif sys.platform == "win32":
        d = Path(os.environ.get("APPDATA", str(Path.home()))) / "ScreenConnect"
    else:
        d = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "ScreenConnect"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_default_config_path(filename: str) -> Path:
    """Return the right config path for the current run mode."""
    if getattr(sys, "frozen", False):
        return get_user_config_dir() / filename
    # Development: look next to the project root
    return Path(__file__).parent.parent.parent / "config" / filename

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8765
    web_port: int = 8080   # mobile web viewer HTTP port


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
    # Output resolution scaling.
    #   scale_mode: "off"     = send at the display's native resolution
    #               "fit"     = scale to fit within target_*, keeping aspect
    #                           (upscales smaller displays, downscales Retina)
    #               "stretch" = force exactly target_* (may distort aspect)
    scale_mode: str = "fit"
    target_width: int = 1920
    target_height: int = 1080


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
            server=ServerConfig(**{k: v for k, v in {**vars(ServerConfig()), **raw.get("server", {})}.items() if k in ServerConfig.__dataclass_fields__}),
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
