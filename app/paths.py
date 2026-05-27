"""
Central path resolution for user-writable files (settings, logs, error.log).

Frozen (packaged) build  → %APPDATA%\\AIInterpretation\\  (Windows)
                         → ~/Library/Application Support/AIInterpretation/ (macOS)
                         → ~/.aiinterpretation/ (Linux)
Development (from source) → project root (next to app/ and gateway/)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def user_data_dir() -> Path:
    """
    Return (and create) the platform-appropriate user data directory.
    Only used when running as a packaged exe; in dev mode use the project root.
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "AIInterpretation"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "AIInterpretation"
    else:
        base = Path.home() / ".aiinterpretation"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _project_root() -> Path:
    """Project root when running from source."""
    return Path(__file__).parent.parent


def settings_path() -> Path:
    """Path to last_settings.json."""
    if getattr(sys, "frozen", False):
        return user_data_dir() / "last_settings.json"
    return _project_root() / "last_settings.json"


def logs_dir() -> Path:
    """Path to the session logs directory (created on demand)."""
    if getattr(sys, "frozen", False):
        p = user_data_dir() / "logs"
    else:
        p = _project_root() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def error_log_path() -> Path:
    """Path to error.log (crash traces from __main__.py)."""
    if getattr(sys, "frozen", False):
        return user_data_dir() / "error.log"
    return _project_root() / "error.log"
