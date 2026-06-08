"""ScreenConnect Agent — entry point.

Usage:
    python agent_main.py
    python agent_main.py --config config/agent.toml
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from src.core.config import Config
from src.core.auth import TokenAuthenticator, UserAccountAuthenticator
from src.core.feature import FeatureRegistry
from src.agent.server import AgentServer
from src.agent.features.screen import ScreenCaptureFeature
from src.agent.features.input import InputFeature
from src.agent.features.clipboard import ClipboardFeature
from src.agent.features.files import FileTransferFeature


def build_auth(cfg: Config):
    if cfg.auth.mode == "users":
        from src.accounts.store import UserStore
        store = UserStore("data/users.json")
        return UserAccountAuthenticator(store)
    return TokenAuthenticator(cfg.auth.token)


def main() -> None:
    parser = argparse.ArgumentParser(description="ScreenConnect Agent")
    parser.add_argument("--config", default="config/agent.toml")
    args = parser.parse_args()

    cfg = Config.load(args.config)

    logging.basicConfig(
        level=getattr(logging, cfg.logging.level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    registry = FeatureRegistry()
    registry.register(ScreenCaptureFeature(cfg))
    registry.register(InputFeature())
    registry.register(ClipboardFeature())
    registry.register(FileTransferFeature(cfg))

    auth = build_auth(cfg)
    server = AgentServer(cfg, registry, auth)

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
