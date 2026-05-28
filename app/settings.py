import customtkinter as ctk

from app.i18n import t, current, set_lang, on_change, remove_callback
from app.theme import palette, current_theme, set_theme, on_theme_change, remove_theme_callback

_LANG_CODES  = ["en", "zh_cn", "zh_tw"]
_LANG_KEYS   = ["lang_en", "lang_zh_cn", "lang_zh_tw"]
_THEME_CODES = ["Light", "Dark"]
_THEME_KEYS  = ["theme_light", "theme_dark"]


class SettingsView(ctk.CTkFrame):
    """Application settings panel, embedded in MainWindow."""

    def __init__(self, parent, main_window):
        p = palette()
        super().__init__(parent, fg_color=p["BG"], corner_radius=0)
        self.main_window = main_window

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._dyn: list[tuple] = []
        self._lang_btns: dict[str, ctk.CTkButton] = {}
        self._theme_btns: dict[str, ctk.CTkButton] = {}
        # Widgets tracked for configure-in-place theme updates
        self._themed: list[tuple] = []

        self._build()
        on_change(self._apply_lang)
        on_theme_change(self._apply_theme)

    # ── Registration helper ────────────────────────────────────────────────────

    def _r(self, widget, **roles):
        """Register widget for theme updates and return it."""
        self._themed.append((widget, roles))
        return widget

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self._build_header()
        self._build_body()

    def _build_header(self) -> None:
        p = palette()
        hdr = self._r(ctk.CTkFrame(self, fg_color=p["SURFACE"], corner_radius=0),
                      fg_color="SURFACE")
        hdr.grid(row=0, column=0, sticky="ew")
        self._r(ctk.CTkFrame(hdr, height=1, fg_color=p["BORDER"]),
                fg_color="BORDER").pack(side="bottom", fill="x")

        inner = ctk.CTkFrame(hdr, fg_color="transparent")
        inner.pack(fill="x", padx=28, pady=14)

        title = self._r(ctk.CTkLabel(inner, text=t("settings"),
                                     font=ctk.CTkFont(size=18, weight="bold"),
                                     text_color=p["TEXT"]),
                        text_color="TEXT")
        title.pack(anchor="w")
        self._dyn.append((title, "settings"))

        sub = self._r(ctk.CTkLabel(inner, text=t("settings_sub"),
                                   font=ctk.CTkFont(size=11), text_color=p["TEXT3"]),
                      text_color="TEXT3")
        sub.pack(anchor="w")
        self._dyn.append((sub, "settings_sub"))

    def _build_body(self) -> None:
        p = palette()
        body = self._r(
            ctk.CTkScrollableFrame(self, fg_color=p["BG"], corner_radius=0,
                                   scrollbar_button_color=p["BORDER"],
                                   scrollbar_button_hover_color=p["TEXT3"]),
            fg_color="BG", scrollbar_button_color="BORDER",
            scrollbar_button_hover_color="TEXT3",
        )
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        wrap = ctk.CTkFrame(body, fg_color="transparent")
        wrap.pack(fill="x", padx=28, pady=(20, 28))

        # ── SYSTEM category ────────────────────────────────────────────────
        cat_lbl = self._r(ctk.CTkLabel(wrap, text=t("cat_system"), anchor="w",
                                       font=ctk.CTkFont(size=10, weight="bold"),
                                       text_color=p["TEXT3"]),
                          text_color="TEXT3")
        cat_lbl.pack(fill="x", pady=(0, 6), padx=2)
        self._dyn.append((cat_lbl, "cat_system"))

        card = self._r(
            ctk.CTkFrame(wrap, fg_color=p["SURFACE"], corner_radius=12,
                         border_width=1, border_color=p["BORDER"]),
            fg_color="SURFACE", border_color="BORDER",
        )
        card.pack(fill="x")
        card.columnconfigure(1, weight=1)

        # ── Language row ───────────────────────────────────────────────────
        lang_lbl = self._r(ctk.CTkLabel(card, text=t("ui_language"), anchor="w",
                                        width=140, font=ctk.CTkFont(size=13),
                                        text_color=p["TEXT"]),
                           text_color="TEXT")
        lang_lbl.grid(row=0, column=0, sticky="w", padx=(20, 12), pady=18)
        self._dyn.append((lang_lbl, "ui_language"))

        toggle = ctk.CTkFrame(card, fg_color="transparent")
        toggle.grid(row=0, column=1, sticky="w", padx=(0, 20), pady=18)

        for code, key in zip(_LANG_CODES, _LANG_KEYS):
            active = code == current()
            btn = ctk.CTkButton(
                toggle, text=t(key), height=34, corner_radius=8,
                fg_color=p["ACCENT"] if active else p["SURFACE"],
                hover_color=p["ACCENT_HV"] if active else p["HOVER_BG"],
                text_color="#ffffff" if active else p["TEXT2"],
                border_width=1,
                border_color=p["ACCENT"] if active else p["BORDER"],
                font=ctk.CTkFont(size=12, weight="bold" if active else "normal"),
                command=lambda c=code: self._select_lang(c),
            )
            btn.pack(side="left", padx=(0, 6))
            self._lang_btns[code] = btn

        # ── Divider ────────────────────────────────────────────────────────
        self._r(ctk.CTkFrame(card, height=1, fg_color=p["BORDER"]),
                fg_color="BORDER").grid(row=1, column=0, columnspan=2,
                                        sticky="ew", padx=20)

        # ── Theme row ─────────────────────────────────────────────────────
        theme_lbl = self._r(ctk.CTkLabel(card, text=t("theme_mode"), anchor="w",
                                         width=140, font=ctk.CTkFont(size=13),
                                         text_color=p["TEXT"]),
                            text_color="TEXT")
        theme_lbl.grid(row=2, column=0, sticky="w", padx=(20, 12), pady=18)
        self._dyn.append((theme_lbl, "theme_mode"))

        theme_toggle = ctk.CTkFrame(card, fg_color="transparent")
        theme_toggle.grid(row=2, column=1, sticky="w", padx=(0, 20), pady=18)

        for code, key in zip(_THEME_CODES, _THEME_KEYS):
            active = code == current_theme()
            btn = ctk.CTkButton(
                theme_toggle, text=t(key), height=34, corner_radius=8,
                fg_color=p["ACCENT"] if active else p["SURFACE"],
                hover_color=p["ACCENT_HV"] if active else p["HOVER_BG"],
                text_color="#ffffff" if active else p["TEXT2"],
                border_width=1,
                border_color=p["ACCENT"] if active else p["BORDER"],
                font=ctk.CTkFont(size=12, weight="bold" if active else "normal"),
                command=lambda c=code: self._select_theme(c),
            )
            btn.pack(side="left", padx=(0, 6))
            self._theme_btns[code] = btn

    # ── Selection handlers ─────────────────────────────────────────────────────

    def _select_lang(self, code: str) -> None:
        set_lang(code)

    def _select_theme(self, code: str) -> None:
        set_theme(code)

    # ── Theme update (configure-in-place) ─────────────────────────────────────

    def _apply_theme(self) -> None:
        p = palette()
        self.configure(fg_color=p["BG"])
        for widget, roles in self._themed:
            if widget.winfo_exists():
                widget.configure(**{k: p[v] for k, v in roles.items()})
        self._refresh_lang_toggle()
        self._refresh_theme_toggle()

    # ── Toggle refreshes ──────────────────────────────────────────────────────

    def _refresh_lang_toggle(self) -> None:
        p = palette()
        sel = current()
        for code, key in zip(_LANG_CODES, _LANG_KEYS):
            btn = self._lang_btns.get(code)
            if btn is None or not btn.winfo_exists():
                continue
            active = code == sel
            btn.configure(
                text=t(key),
                fg_color=p["ACCENT"] if active else p["SURFACE"],
                hover_color=p["ACCENT_HV"] if active else p["HOVER_BG"],
                text_color="#ffffff" if active else p["TEXT2"],
                border_color=p["ACCENT"] if active else p["BORDER"],
                font=ctk.CTkFont(size=12, weight="bold" if active else "normal"),
            )

    def _refresh_theme_toggle(self) -> None:
        p = palette()
        for code, key in zip(_THEME_CODES, _THEME_KEYS):
            btn = self._theme_btns.get(code)
            if btn is None or not btn.winfo_exists():
                continue
            active = code == current_theme()
            btn.configure(
                text=t(key),
                fg_color=p["ACCENT"] if active else p["SURFACE"],
                hover_color=p["ACCENT_HV"] if active else p["HOVER_BG"],
                text_color="#ffffff" if active else p["TEXT2"],
                border_color=p["ACCENT"] if active else p["BORDER"],
                font=ctk.CTkFont(size=12, weight="bold" if active else "normal"),
            )

    # ── Language update callback ───────────────────────────────────────────────

    def _apply_lang(self) -> None:
        for widget, key in self._dyn:
            widget.configure(text=t(key))
        self._refresh_lang_toggle()
        self._refresh_theme_toggle()

    def on_show(self) -> None:
        self._refresh_lang_toggle()
        self._refresh_theme_toggle()
