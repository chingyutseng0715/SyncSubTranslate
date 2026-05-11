"""Draws the app icon at runtime using Pillow — no external image file needed."""
from __future__ import annotations

try:
    from PIL import Image, ImageDraw, ImageTk
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

_cached: "ImageTk.PhotoImage | None" = None


def _draw(size: int = 256) -> "Image.Image":
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = size // 2
    s = size / 256  # scale factor

    # Background — dark blue rounded square
    r = int(size * 0.18)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill="#1F6AA5")

    # Mic capsule
    draw.rounded_rectangle(
        [cx - int(28 * s), int(38 * s), cx + int(28 * s), int(145 * s)],
        radius=int(28 * s),
        fill="white",
    )

    # Stand arc (bottom half of ellipse = downward curve)
    lw = max(1, int(8 * s))
    draw.arc(
        [cx - int(52 * s), int(108 * s), cx + int(52 * s), int(196 * s)],
        start=0, end=180,
        fill="white", width=lw,
    )

    # Vertical stem
    hw = max(1, int(4 * s))
    draw.rectangle(
        [cx - hw, int(196 * s), cx + hw, int(220 * s)],
        fill="white",
    )

    # Base bar
    draw.rounded_rectangle(
        [cx - int(36 * s), int(215 * s), cx + int(36 * s), int(226 * s)],
        radius=max(1, int(4 * s)),
        fill="white",
    )

    return img


def apply(window) -> None:
    """Set the app icon on any tkinter / customtkinter window."""
    if not _PIL_OK:
        return
    global _cached
    if _cached is None:
        _cached = ImageTk.PhotoImage(_draw(256))
    try:
        window.iconphoto(False, _cached)
    except Exception:
        pass
