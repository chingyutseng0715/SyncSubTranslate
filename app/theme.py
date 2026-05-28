"""Shared theme state — light/dark palette + change callbacks."""
from __future__ import annotations
import json
import customtkinter as ctk

_LIGHT: dict[str, str] = {
    "BG":           "#f5f6fa",
    "SIDEBAR":      "#ffffff",
    "SURFACE":      "#ffffff",
    "ACCENT":       "#3b82f6",
    "ACCENT_HV":    "#2563eb",
    "ACCENT_LT":    "#eff6ff",
    "ACCENT_BORDER":"#bfdbfe",
    "TEXT":         "#111827",
    "TEXT2":        "#6b7280",
    "TEXT3":        "#9ca3af",
    "BORDER":       "#e5e7eb",
    "HOVER_BG":     "#f3f4f6",
}

_DARK: dict[str, str] = {
    "BG":           "#1f2937",
    "SIDEBAR":      "#111827",
    "SURFACE":      "#374151",
    "ACCENT":       "#3b82f6",
    "ACCENT_HV":    "#2563eb",
    "ACCENT_LT":    "#1e3a5f",
    "ACCENT_BORDER":"#374151",
    "TEXT":         "#f9fafb",
    "TEXT2":        "#d1d5db",
    "TEXT3":        "#9ca3af",
    "BORDER":       "#4b5563",
    "HOVER_BG":     "#4b5563",
}

_current: str = "Light"
_CALLBACKS: list = []


def palette() -> dict[str, str]:
    return _DARK if _current == "Dark" else _LIGHT


def current_theme() -> str:
    return _current


def set_theme(code: str) -> None:
    global _current
    if code not in ("Light", "Dark"):
        return
    _current = code
    ctk.set_appearance_mode(code)
    _save_to_disk(code)
    for cb in list(_CALLBACKS):
        try:
            cb()
        except Exception:
            pass


def on_theme_change(callback) -> None:
    if callback not in _CALLBACKS:
        _CALLBACKS.append(callback)


def remove_theme_callback(callback) -> None:
    if callback in _CALLBACKS:
        _CALLBACKS.remove(callback)


def load_and_apply() -> None:
    """Read saved theme from disk and apply. Call once at startup before any windows open."""
    global _current
    try:
        from app.paths import settings_path
        data = json.loads(settings_path().read_text(encoding="utf-8"))
        code = data.get("app_theme", "Light")
        if code not in ("Light", "Dark"):
            code = "Light"
        _current = code
    except Exception:
        pass
    ctk.set_appearance_mode(_current)


def _save_to_disk(code: str) -> None:
    try:
        from app.paths import settings_path
        path = settings_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        data["app_theme"] = code
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass
