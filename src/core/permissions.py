"""Platform permission checks for remote control.

On macOS, injecting synthetic keyboard/mouse events requires the
*Accessibility* permission (System Settings → Privacy & Security →
Accessibility). Capturing the screen requires *Screen Recording*.

These helpers let the agent detect whether control is allowed and guide
the user to grant it, instead of silently failing to inject input.

On Windows and Linux there is no equivalent per-app gate, so the control
checks return True.
"""
from __future__ import annotations

import logging
import subprocess
import sys
import time

log = logging.getLogger(__name__)

_IS_MAC = sys.platform == "darwin"

# Deep links into System Settings → Privacy & Security
ACCESSIBILITY_SETTINGS_URL = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
)
SCREEN_SETTINGS_URL = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
)

# AXIsProcessTrusted() is cheap but we may call it on every input event,
# so cache the result for a short window.
_CACHE_TTL = 1.5
_cache: dict[str, float | bool | None] = {"value": None, "ts": 0.0}


def _query_ax_trusted() -> bool:
    """Call the native AXIsProcessTrusted() via ctypes."""
    import ctypes
    import ctypes.util

    path = ctypes.util.find_library("ApplicationServices")
    if not path:
        return True
    lib = ctypes.cdll.LoadLibrary(path)
    lib.AXIsProcessTrusted.restype = ctypes.c_bool
    return bool(lib.AXIsProcessTrusted())


def _set_cache(value: bool) -> None:
    _cache["value"] = value
    _cache["ts"] = time.monotonic()


def control_granted(*, use_cache: bool = True) -> bool:
    """True if this process may inject keyboard/mouse events.

    On macOS this reflects the Accessibility permission. On other
    platforms it always returns True.
    """
    if not _IS_MAC:
        return True
    now = time.monotonic()
    if use_cache and _cache["value"] is not None and (now - float(_cache["ts"])) < _CACHE_TTL:
        return bool(_cache["value"])
    try:
        value = _query_ax_trusted()
    except Exception as e:  # pragma: no cover - platform specific
        log.warning("Could not check Accessibility permission: %s", e)
        value = True  # fail open rather than lock the user out entirely
    _set_cache(value)
    return value


def request_control() -> bool:
    """Trigger the macOS Accessibility prompt; return the current state.

    Shows the system "allow X to control this computer" dialog the first
    time. If already granted, no dialog appears. Returns the (possibly
    still False) granted state immediately — the user grants it
    asynchronously in System Settings.
    """
    if not _IS_MAC:
        return True
    try:
        # PyObjC is a pynput dependency on macOS, so this is normally present.
        from ApplicationServices import (  # type: ignore
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )
        granted = bool(
            AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
        )
        _set_cache(granted)
        return granted
    except Exception as e:
        log.debug("AX prompt via PyObjC unavailable (%s); falling back.", e)
        return control_granted(use_cache=False)


def open_control_settings() -> None:
    """Open System Settings → Privacy & Security → Accessibility."""
    if _IS_MAC:
        subprocess.Popen(["open", ACCESSIBILITY_SETTINGS_URL])


def open_screen_settings() -> None:
    """Open System Settings → Privacy & Security → Screen Recording."""
    if _IS_MAC:
        subprocess.Popen(["open", SCREEN_SETTINGS_URL])
