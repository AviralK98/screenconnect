"""ScreenConnect Viewer — entry point.

Usage:
    python viewer_main.py
    python viewer_main.py --config config/viewer.toml
    python viewer_main.py --host 192.168.1.50
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from src.core.config import Config
from src.core.auth import TokenAuthenticator, UserAccountAuthenticator
from src.core.feature import FeatureRegistry
from src.viewer.client import ViewerClient
from src.viewer.features.display import DisplayFeature
from src.viewer.features.input import InputCaptureFeature
from src.viewer.features.clipboard import ClipboardFeature
from src.viewer.features.files import FileTransferFeature


def build_auth(cfg: Config):
    if cfg.auth.mode == "users":
        from src.accounts.store import UserStore
        store = UserStore("data/users.json")
        return UserAccountAuthenticator(
            store,
            username=cfg.auth.username,
            password=cfg.auth.password,
        )
    return TokenAuthenticator(cfg.auth.token)


async def _monitor_cycle(session, transport):
    """Cycle to the next monitor and send monitor_select."""
    from src.core.protocol import Message, MessageType
    if not session.monitors:
        return
    next_id = (session.selected_monitor + 1) % len(session.monitors)
    session.selected_monitor = next_id
    await transport.send_message(Message(MessageType.MONITOR_SELECT, {"monitor_id": next_id}))


def main() -> None:
    parser = argparse.ArgumentParser(description="ScreenConnect Viewer")
    parser.add_argument("--config", default="config/viewer.toml")
    parser.add_argument("--host", help="Override agent host")
    args = parser.parse_args()

    cfg = Config.load(args.config)
    if args.host:
        cfg.server.host = args.host

    logging.basicConfig(
        level=getattr(logging, cfg.logging.level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    display   = DisplayFeature()
    clipboard = ClipboardFeature()
    files     = FileTransferFeature(cfg)
    input_cap = InputCaptureFeature(
        display_feature=display,
        clipboard_feature=clipboard,
        monitor_cycle_cb=_monitor_cycle,
    )

    registry = FeatureRegistry()
    registry.register(display)
    registry.register(input_cap)
    registry.register(clipboard)
    registry.register(files)

    auth = build_auth(cfg)
    client = ViewerClient(cfg, registry, auth)

    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        pass
    finally:
        display.destroy()


if __name__ == "__main__":
    main()
