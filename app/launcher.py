import customtkinter as ctk
from app import icon
from app.i18n import t, on_change
from app.theme import palette as _theme_palette, on_theme_change

# ── Design tokens — synced from app.theme on load and on theme change ──────────
_BG        = "#f5f6fa"
_SIDEBAR   = "#ffffff"
_SURFACE   = "#ffffff"
_ACCENT    = "#3b82f6"
_ACCENT_HV = "#2563eb"
_ACCENT_LT = "#eff6ff"
_TEXT      = "#111827"
_TEXT2     = "#6b7280"
_TEXT3     = "#9ca3af"
_BORDER    = "#e5e7eb"
_HOVER_BG  = "#f3f4f6"

SIDEBAR_W  = 214


def _sync_colors() -> None:
    p = _theme_palette()
    global _BG, _SIDEBAR, _SURFACE, _ACCENT, _ACCENT_HV, _ACCENT_LT
    global _TEXT, _TEXT2, _TEXT3, _BORDER, _HOVER_BG
    _BG = p["BG"]; _SIDEBAR = p["SIDEBAR"]; _SURFACE = p["SURFACE"]
    _ACCENT = p["ACCENT"]; _ACCENT_HV = p["ACCENT_HV"]; _ACCENT_LT = p["ACCENT_LT"]
    _TEXT = p["TEXT"]; _TEXT2 = p["TEXT2"]; _TEXT3 = p["TEXT3"]
    _BORDER = p["BORDER"]; _HOVER_BG = p["HOVER_BG"]


_sync_colors()  # sync at module load so initial colors match saved theme


class MainWindow(ctk.CTkToplevel):
    """Single-window shell: sidebar navigation + swappable content views."""

    def __init__(self, root: ctk.CTk):
        super().__init__(root)
        self.root = root
        self.title("AI Interpretation")
        self.geometry("980x660")
        self.minsize(820, 520)
        self.protocol("WM_DELETE_WINDOW", root.destroy)
        self.configure(fg_color=_SIDEBAR)

        self._views: dict[str, ctk.CTkFrame] = {}
        self._nav_btns: dict[str, ctk.CTkButton] = {}
        self._active: str | None = None
        # (widget, i18n_key) pairs updated on language change
        self._dyn: list[tuple] = []
        # Sidebar widgets tracked for configure-in-place theme updates
        self._themed_sb: list[tuple] = []

        self._build_layout()
        self._build_sidebar()
        self._center(980, 660)
        icon.apply(self)
        on_change(self._apply_lang)
        on_theme_change(self._apply_theme)
        self.lift()
        self.focus_force()
        self._switch("service")

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build_layout(self) -> None:
        """Create the fixed layout skeleton (content area). Called once."""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._content = ctk.CTkFrame(self, fg_color=_BG, corner_radius=0)
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

    def _build_sidebar(self) -> None:
        """Build the sidebar once. Registers all widgets in _themed_sb."""
        def _r(widget, **roles):
            self._themed_sb.append((widget, roles))
            return widget

        # ── Sidebar frame ──────────────────────────────────────────────────
        sb = _r(ctk.CTkFrame(self, fg_color=_SIDEBAR, corner_radius=0, width=SIDEBAR_W),
                fg_color="SIDEBAR")
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)
        sb.grid_rowconfigure(2, weight=1)

        # App brand
        brand = ctk.CTkFrame(sb, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=20, pady=(24, 20))

        title_row = ctk.CTkFrame(brand, fg_color="transparent")
        title_row.pack(anchor="w")
        _r(ctk.CTkLabel(title_row, text="AI ",
                        font=ctk.CTkFont(size=18, weight="bold"), text_color=_TEXT),
           text_color="TEXT").pack(side="left")
        ctk.CTkLabel(title_row, text="Live",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#7dd3fc").pack(side="left")

        brand_sub = _r(ctk.CTkLabel(brand, text=t("interp_system"),
                                    font=ctk.CTkFont(size=10), text_color=_TEXT3, anchor="w"),
                       text_color="TEXT3")
        brand_sub.pack(anchor="w")
        self._dyn.append((brand_sub, "interp_system"))

        # Divider below brand
        _r(ctk.CTkFrame(sb, height=1, fg_color=_BORDER),
           fg_color="BORDER").grid(row=0, column=0, sticky="sew")

        # Nav section
        nav = ctk.CTkFrame(sb, fg_color="transparent")
        nav.grid(row=1, column=0, sticky="nsew", padx=12, pady=(14, 0))
        nav.columnconfigure(0, weight=1)

        main_lbl = _r(ctk.CTkLabel(nav, text=t("main_section"), anchor="w",
                                   font=ctk.CTkFont(size=9, weight="bold"), text_color=_TEXT3),
                      text_color="TEXT3")
        main_lbl.grid(row=0, column=0, sticky="w", padx=10, pady=(0, 6))
        self._dyn.append((main_lbl, "main_section"))

        nav_items = [
            ("service", "▶", "subtitle_service"),
            ("monitor", "⬡", "monitor_center"),
        ]
        for i, (key, sym, lang_key) in enumerate(nav_items):
            btn = ctk.CTkButton(
                nav,
                text=f"  {sym}   {t(lang_key)}",
                anchor="w", height=42, corner_radius=8,
                fg_color="transparent", hover_color=_HOVER_BG,
                text_color=_TEXT2, font=ctk.CTkFont(size=13),
                command=lambda k=key: self._switch(k),
            )
            btn.grid(row=i + 1, column=0, sticky="ew", pady=2)
            self._nav_btns[key] = btn
            self._dyn.append((btn, lambda s=sym, k=lang_key: f"  {s}   {t(k)}"))

        # ── Bottom: Settings + version ─────────────────────────────────────
        _r(ctk.CTkFrame(sb, height=1, fg_color=_BORDER),
           fg_color="BORDER").grid(row=3, column=0, sticky="ew")

        bottom_nav = ctk.CTkFrame(sb, fg_color="transparent")
        bottom_nav.grid(row=4, column=0, sticky="ew", padx=12, pady=(8, 4))
        bottom_nav.columnconfigure(0, weight=1)

        settings_btn = ctk.CTkButton(
            bottom_nav,
            text=f"  ⚙   {t('settings')}",
            anchor="w", height=42, corner_radius=8,
            fg_color="transparent", hover_color=_HOVER_BG,
            text_color=_TEXT2, border_width=1, border_color=_BORDER,
            font=ctk.CTkFont(size=13),
            command=lambda: self._switch("settings"),
        )
        settings_btn.grid(row=0, column=0, sticky="ew", pady=2)
        self._nav_btns["settings"] = settings_btn
        self._dyn.append((settings_btn, lambda: f"  ⚙   {t('settings')}"))

        _r(ctk.CTkLabel(sb, text="v1.1.15",
                        font=ctk.CTkFont(size=10), text_color=_TEXT3),
           text_color="TEXT3").grid(row=5, column=0, pady=(0, 14))

        # Right edge border
        _r(ctk.CTkFrame(self, width=1, fg_color=_BORDER),
           fg_color="BORDER").grid(row=0, column=0, sticky="nse")

    # ── Theme update ───────────────────────────────────────────────────────────

    def _apply_theme(self) -> None:
        _sync_colors()
        p = _theme_palette()
        # Window shell + content area
        self.configure(fg_color=p["SIDEBAR"])
        self._content.configure(fg_color=p["BG"])
        # All tracked sidebar widgets
        for widget, roles in self._themed_sb:
            if widget.winfo_exists():
                widget.configure(**{k: p[v] for k, v in roles.items()})
        # Nav buttons — active vs inactive state
        for k, btn in self._nav_btns.items():
            if k == self._active:
                btn.configure(fg_color=p["ACCENT_LT"], text_color=p["ACCENT"],
                              hover_color=p["ACCENT_LT"],
                              font=ctk.CTkFont(size=13, weight="bold"))
            else:
                kw = dict(fg_color="transparent", text_color=p["TEXT2"],
                          hover_color=p["HOVER_BG"], font=ctk.CTkFont(size=13))
                if k == "settings":
                    kw["border_color"] = p["BORDER"]
                btn.configure(**kw)

    # ── Language update ────────────────────────────────────────────────────────

    def _apply_lang(self) -> None:
        for widget, key_or_fn in self._dyn:
            if callable(key_or_fn):
                widget.configure(text=key_or_fn())
            else:
                widget.configure(text=t(key_or_fn))

    # ── View switching ─────────────────────────────────────────────────────────

    def _switch(self, key: str) -> None:
        if key not in self._views:
            if key == "service":
                from app.service import ServiceView
                view = ServiceView(self._content, main_window=self)
            elif key == "monitor":
                from app.monitor import MonitorView
                view = MonitorView(self._content, main_window=self)
            elif key == "settings":
                from app.settings import SettingsView
                view = SettingsView(self._content, main_window=self)
            else:
                return
            view.grid(row=0, column=0, sticky="nsew")
            self._views[key] = view

        for k, v in self._views.items():
            if k == key:
                v.grid()
                v.tkraise()
            else:
                v.grid_remove()

        for k, btn in self._nav_btns.items():
            if k == key:
                btn.configure(
                    fg_color=_ACCENT_LT, text_color=_ACCENT,
                    font=ctk.CTkFont(size=13, weight="bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent", text_color=_TEXT2,
                    font=ctk.CTkFont(size=13),
                )
        self._active = key

        if hasattr(self._views.get(key), "on_show"):
            self._views[key].on_show()


LauncherWindow = MainWindow
