import customtkinter as ctk
from app.i18n import t, current, set_lang, on_change, remove_callback

# ── Design tokens (keep in sync with launcher.py) ─────────────────────────────
_BG        = "#f5f6fa"
_SURFACE   = "#ffffff"
_ACCENT    = "#3b82f6"
_ACCENT_HV = "#2563eb"
_ACCENT_LT = "#eff6ff"
_TEXT      = "#111827"
_TEXT2     = "#6b7280"
_TEXT3     = "#9ca3af"
_BORDER    = "#e5e7eb"
_HOVER_BG  = "#f3f4f6"

_LANG_CODES = ["en", "zh_cn", "zh_tw"]
_LANG_KEYS  = ["lang_en", "lang_zh_cn", "lang_zh_tw"]


class SettingsView(ctk.CTkFrame):
    """Application settings panel, embedded in MainWindow."""

    def __init__(self, parent, main_window):
        super().__init__(parent, fg_color=_BG, corner_radius=0)
        self.main_window = main_window

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Widgets that need text updates on language change
        self._dyn: list[tuple] = []
        # The language toggle buttons {code: CTkButton}
        self._lang_btns: dict[str, ctk.CTkButton] = {}

        self._build()
        on_change(self._apply_lang)

    def _build(self) -> None:
        self._build_header()
        self._build_body()

    # ── Header ─────────────────────────────────────────────────────────────────

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color=_SURFACE, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkFrame(hdr, height=1, fg_color=_BORDER).pack(side="bottom", fill="x")

        inner = ctk.CTkFrame(hdr, fg_color="transparent")
        inner.pack(fill="x", padx=28, pady=14)

        title = ctk.CTkLabel(
            inner, text=t("settings"),
            font=ctk.CTkFont(size=18, weight="bold"), text_color=_TEXT,
        )
        title.pack(anchor="w")
        self._dyn.append((title, "settings"))

        sub = ctk.CTkLabel(
            inner, text=t("settings_sub"),
            font=ctk.CTkFont(size=11), text_color=_TEXT3,
        )
        sub.pack(anchor="w")
        self._dyn.append((sub, "settings_sub"))

    # ── Body ───────────────────────────────────────────────────────────────────

    def _build_body(self) -> None:
        body = ctk.CTkScrollableFrame(
            self, fg_color=_BG, corner_radius=0,
            scrollbar_button_color=_BORDER,
            scrollbar_button_hover_color=_TEXT3,
        )
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        wrap = ctk.CTkFrame(body, fg_color="transparent")
        wrap.pack(fill="x", padx=28, pady=(20, 28))

        # ── SYSTEM category ────────────────────────────────────────────────
        cat_lbl = ctk.CTkLabel(
            wrap, text=t("cat_system"), anchor="w",
            font=ctk.CTkFont(size=10, weight="bold"), text_color=_TEXT3,
        )
        cat_lbl.pack(fill="x", pady=(0, 6), padx=2)
        self._dyn.append((cat_lbl, "cat_system"))

        card = ctk.CTkFrame(
            wrap, fg_color=_SURFACE, corner_radius=12,
            border_width=1, border_color=_BORDER,
        )
        card.pack(fill="x")
        card.columnconfigure(1, weight=1)

        # Language row label
        lang_lbl = ctk.CTkLabel(
            card, text=t("ui_language"), anchor="w", width=140,
            font=ctk.CTkFont(size=13), text_color=_TEXT,
        )
        lang_lbl.grid(row=0, column=0, sticky="w", padx=(20, 12), pady=18)
        self._dyn.append((lang_lbl, "ui_language"))

        # Three-button language toggle
        toggle = ctk.CTkFrame(card, fg_color="transparent")
        toggle.grid(row=0, column=1, sticky="w", padx=(0, 20), pady=18)

        for code, key in zip(_LANG_CODES, _LANG_KEYS):
            btn = ctk.CTkButton(
                toggle,
                text=t(key),
                height=34,
                corner_radius=8,
                fg_color=_ACCENT if code == current() else _SURFACE,
                hover_color=_ACCENT_HV if code == current() else _HOVER_BG,
                text_color="#ffffff" if code == current() else _TEXT2,
                border_width=1,
                border_color=_ACCENT if code == current() else _BORDER,
                font=ctk.CTkFont(
                    size=12,
                    weight="bold" if code == current() else "normal",
                ),
                command=lambda c=code: self._select_lang(c),
            )
            btn.pack(side="left", padx=(0, 6))
            self._lang_btns[code] = btn

    # ── Language selection ─────────────────────────────────────────────────────

    def _select_lang(self, code: str) -> None:
        set_lang(code)   # fires _apply_lang on all registered views

    def _refresh_toggle(self) -> None:
        """Re-style the three toggle buttons to reflect the current selection."""
        sel = current()
        for code, key in zip(_LANG_CODES, _LANG_KEYS):
            btn = self._lang_btns[code]
            active = code == sel
            btn.configure(
                text=t(key),
                fg_color=_ACCENT if active else _SURFACE,
                hover_color=_ACCENT_HV if active else _HOVER_BG,
                text_color="#ffffff" if active else _TEXT2,
                border_color=_ACCENT if active else _BORDER,
                font=ctk.CTkFont(size=12, weight="bold" if active else "normal"),
            )

    # ── Language update callback ───────────────────────────────────────────────

    def _apply_lang(self) -> None:
        for widget, key in self._dyn:
            widget.configure(text=t(key))
        self._refresh_toggle()

    def on_show(self) -> None:
        self._refresh_toggle()
