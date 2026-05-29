import json
import sys
import threading
import time
import urllib.request
import webbrowser

import customtkinter as ctk

try:
    import pyaudio
    _PYAUDIO_OK = True
except Exception:
    _PYAUDIO_OK = False

from app.heartbeat import HeartbeatSender
from app.runner import GatewayRunner
from app.i18n import t, on_change
from app.paths import settings_path as _settings_path
from app.theme import palette as _theme_palette, on_theme_change


# ── Design tokens — synced from app.theme ─────────────────────────────────────
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
# Stop-state button uses semantic red — constant across themes
_STOP_BG   = "#fef2f2"
_STOP_TEXT = "#dc2626"
_STOP_HV   = "#fee2e2"


def _sync_colors() -> None:
    p = _theme_palette()
    global _BG, _SURFACE, _ACCENT, _ACCENT_HV, _ACCENT_LT
    global _TEXT, _TEXT2, _TEXT3, _BORDER, _HOVER_BG
    _BG = p["BG"]; _SURFACE = p["SURFACE"]; _ACCENT = p["ACCENT"]
    _ACCENT_HV = p["ACCENT_HV"]; _ACCENT_LT = p["ACCENT_LT"]
    _TEXT = p["TEXT"]; _TEXT2 = p["TEXT2"]; _TEXT3 = p["TEXT3"]
    _BORDER = p["BORDER"]; _HOVER_BG = p["HOVER_BG"]


_sync_colors()  # sync at module load

_COLORS = {
    "White":        "#ffffff",
    "Red":          "#f87171",
    "Yellow":       "#ffff00",
    "Light Yellow": "#fef9c3",
    "Blue":         "#7dd3fc",
    "Green":        "#4ade80",
    "Pink":         "#f472b6",
    "Leaf Green":   "#22c55e",
    "Dark Blue":    "#1d4ed8",
}

_BG_COLORS = {
    "Black":     "#000000",
    "Dark Grey": "#1f2937",
    "Dark Blue": "#0f172a",
}


# ── Windows Core Audio: enumerate only DEVICE_STATE_ACTIVE capture endpoints ──

def _win_active_mics() -> tuple[list[str], str | None]:
    """
    Use Windows IMMDeviceEnumerator to list only *active* (plugged-in, enabled)
    audio capture endpoints — the same set Microsoft Teams shows.

    Returns (active_names, default_name):
      active_names — FriendlyName of each DEVICE_STATE_ACTIVE capture endpoint
      default_name — FriendlyName of the eCapture/eConsole default, or None
    Returns ([], None) on non-Windows or any COM error (caller falls back).
    """
    if sys.platform != "win32":
        return [], None
    try:
        import ctypes
        import uuid as _uuid

        ole32 = ctypes.windll.ole32
        ole32.CoInitializeEx(None, 2)       # COINIT_MULTITHREADED; ignore return value

        def _guid(s: str) -> ctypes.Array:
            return (ctypes.c_byte * 16)(*_uuid.UUID(s).bytes_le)

        def _vt(p: ctypes.c_void_p) -> ctypes.POINTER(ctypes.c_void_p):
            """Return the vtable pointer array for a COM interface pointer."""
            vtbl = ctypes.c_void_p.from_address(p.value).value
            return ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))

        def _rel(p: ctypes.c_void_p) -> None:
            if p and p.value:
                ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(_vt(p)[2])(p)

        # Create IMMDeviceEnumerator ------------------------------------------
        p_enum = ctypes.c_void_p()
        if ole32.CoCreateInstance(
            _guid("BCDE0395-E52F-467C-8E3D-C4579291692E"),  # CLSID_MMDeviceEnumerator
            None, 23,                                        # CLSCTX_ALL
            _guid("A95664D2-9614-4F35-A746-DE8DB63617E6"),  # IID_IMMDeviceEnumerator
            ctypes.byref(p_enum),
        ) != 0 or not p_enum.value:
            return [], None
        ev = _vt(p_enum)

        # IMMDeviceEnumerator vtable: QI AddRef Release Enum(3) GetDefault(4)
        EnumEndpoints = ctypes.WINFUNCTYPE(
            ctypes.HRESULT, ctypes.c_void_p,
            ctypes.c_int, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p),
        )(ev[3])
        GetDefault = ctypes.WINFUNCTYPE(
            ctypes.HRESULT, ctypes.c_void_p,
            ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p),
        )(ev[4])

        # PKEY_Device_FriendlyName = {A45C254E-DF1C-4EFD-8020-67D146A850E0}, pid=14
        class _PROPKEY(ctypes.Structure):
            _fields_ = [("fmtid", ctypes.c_byte * 16), ("pid", ctypes.c_uint32)]

        pkey = _PROPKEY()
        ctypes.memmove(pkey.fmtid, _guid("A45C254E-DF1C-4EFD-8020-67D146A850E0"), 16)
        pkey.pid = 14

        # PROPVARIANT (64-bit layout: 8-byte header + 8-byte union + 8-byte pad = 24 bytes)
        class _PROPVAR(ctypes.Structure):
            _fields_ = [
                ("vt", ctypes.c_uint16), ("r1", ctypes.c_uint16),
                ("r2", ctypes.c_uint16), ("r3", ctypes.c_uint16),
                ("ptr", ctypes.c_size_t),   # VT_LPWSTR (31) → wchar_t*
                ("_x",  ctypes.c_uint64),   # padding for DECIMAL union member
            ]

        def _get_name(p_dev: ctypes.c_void_p) -> str | None:
            """Read PKEY_Device_FriendlyName from an IMMDevice via IPropertyStore."""
            # IMMDevice vtable: QI AddRef Release Activate OpenPropertyStore(4)
            OpenStore = ctypes.WINFUNCTYPE(
                ctypes.HRESULT, ctypes.c_void_p,
                ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p),
            )(_vt(p_dev)[4])
            p_store = ctypes.c_void_p()
            if OpenStore(p_dev, 0, ctypes.byref(p_store)) != 0 or not p_store.value:
                return None
            # IPropertyStore vtable: QI AddRef Release GetCount GetAt GetValue(5)
            GetValue = ctypes.WINFUNCTYPE(
                ctypes.HRESULT, ctypes.c_void_p,
                ctypes.POINTER(_PROPKEY), ctypes.POINTER(_PROPVAR),
            )(_vt(p_store)[5])
            pv = _PROPVAR()
            name: str | None = None
            if GetValue(p_store, ctypes.byref(pkey), ctypes.byref(pv)) == 0:
                if pv.vt == 31 and pv.ptr:             # VT_LPWSTR = 31
                    name = ctypes.cast(pv.ptr, ctypes.c_wchar_p).value
                    ole32.CoTaskMemFree(ctypes.c_void_p(pv.ptr))
            _rel(p_store)
            return name

        # Enumerate DEVICE_STATE_ACTIVE (1) capture endpoints (eCapture=1) ----
        p_coll = ctypes.c_void_p()
        if EnumEndpoints(p_enum, 1, 1, ctypes.byref(p_coll)) != 0 or not p_coll.value:
            _rel(p_enum)
            return [], None
        cv = _vt(p_coll)
        GetCount = ctypes.WINFUNCTYPE(
            ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32),
        )(cv[3])
        Item = ctypes.WINFUNCTYPE(
            ctypes.HRESULT, ctypes.c_void_p,
            ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p),
        )(cv[4])

        n = ctypes.c_uint32(0)
        GetCount(p_coll, ctypes.byref(n))
        active: list[str] = []
        for i in range(n.value):
            p_dev = ctypes.c_void_p()
            if Item(p_coll, i, ctypes.byref(p_dev)) == 0 and p_dev.value:
                nm = _get_name(p_dev)
                if nm:
                    active.append(nm)
                _rel(p_dev)
        _rel(p_coll)

        # Get eCapture/eConsole default device --------------------------------
        p_def = ctypes.c_void_p()
        default: str | None = None
        if GetDefault(p_enum, 1, 0, ctypes.byref(p_def)) == 0 and p_def.value:
            default = _get_name(p_def)
            _rel(p_def)

        _rel(p_enum)
        return active, default

    except Exception:
        return [], None


class ServiceView(ctk.CTkFrame):
    """Subtitle Service configuration and control, embedded in MainWindow."""

    def __init__(self, parent, main_window):
        super().__init__(parent, fg_color=_BG, corner_radius=0)
        self.main_window = main_window

        self._runner = GatewayRunner()
        self._sender = HeartbeatSender()
        self._mic_devices: list[tuple[int | None, str]] = []
        self._health: dict = {}
        self._health_stop = threading.Event()

        # i18n: (widget, key) pairs updated on language change
        self._dyn: list[tuple] = []
        self._form_widgets: list = []
        # Tracks the i18n key for the current status label state
        self._status_key = "status_idle"
        # Widgets tracked for configure-in-place theme updates
        self._themed: list[tuple] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._init_vars()   # create StringVars once; they survive theme rebuilds
        self._build()
        self._refresh_mics()
        on_change(self._apply_lang)
        on_theme_change(self._apply_theme)

    # ── StringVar initialisation (survives theme rebuilds) ────────────────────

    def _init_vars(self) -> None:
        self._room_var     = ctk.StringVar(value="Room 1")
        self._api_var      = ctk.StringVar()
        self._monitor_var  = ctk.StringVar()
        self._display_var  = ctk.StringVar(value="Both")
        self._zh_size_var  = ctk.StringVar(value="30")
        self._en_size_var  = ctk.StringVar(value="30")
        self._zh_color_var = ctk.StringVar(value="Blue")
        self._en_color_var = ctk.StringVar(value="Green")
        self._bg_var       = ctk.StringVar(value="Black")
        self._lang_var     = ctk.StringVar(value="Chinese ↔ English")
        self._mic_var      = ctk.StringVar(value="Scanning...")
        self._asr_var      = ctk.StringVar(value="qwen3-asr-flash-realtime-2026-02-10")
        self._translate_var = ctk.StringVar(value="qwen-plus")

    # ── Theme update (configure-in-place) ────────────────────────────────────

    def _apply_theme(self) -> None:
        _sync_colors()
        p = _theme_palette()
        self.configure(fg_color=p["BG"])
        for widget, roles in self._themed:
            if widget.winfo_exists():
                widget.configure(**{k: p[v] for k, v in roles.items()})
        # Start button uses accent colors only when not running (stop state is semantic red)
        if not self._runner.running:
            self._start_btn.configure(fg_color=p["ACCENT"], hover_color=p["ACCENT_HV"])

    # ── Registration helper ────────────────────────────────────────────────────

    def _r(self, widget, **roles):
        """Register widget for theme updates and return it."""
        self._themed.append((widget, roles))
        return widget

    # ── Build UI ───────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self._build_header()
        self._build_body()

    def _build_header(self) -> None:
        hdr = self._r(ctk.CTkFrame(self, fg_color=_SURFACE, corner_radius=0),
                      fg_color="SURFACE")
        hdr.grid(row=0, column=0, sticky="ew")
        self._r(ctk.CTkFrame(hdr, height=1, fg_color=_BORDER),
                fg_color="BORDER").pack(side="bottom", fill="x")

        inner = ctk.CTkFrame(hdr, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=12)

        self._status_lbl = self._r(
            ctk.CTkLabel(inner, text=t("status_idle"),
                         font=ctk.CTkFont(size=12), text_color=_TEXT3,
                         width=130, anchor="w"),
            text_color="TEXT3",
        )
        self._status_lbl.pack(side="left", padx=(8, 12))

        btn_bar = ctk.CTkFrame(inner, fg_color="transparent")
        btn_bar.pack(side="left", fill="x", expand=True)
        btn_bar.columnconfigure((0, 1, 2), weight=1)

        self._load_btn = self._r(
            ctk.CTkButton(btn_bar, text=t("use_last"),
                          height=38, corner_radius=8,
                          fg_color=_BG, hover_color=_HOVER_BG,
                          text_color=_TEXT2, border_width=1, border_color=_BORDER,
                          font=ctk.CTkFont(size=12),
                          state="normal" if _settings_path().exists() else "disabled",
                          command=self._apply_saved_settings),
            fg_color="BG", hover_color="HOVER_BG", text_color="TEXT2", border_color="BORDER",
        )
        self._load_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._dyn.append((self._load_btn, "use_last"))

        self._browser_btn = self._r(
            ctk.CTkButton(btn_bar, text=t("open_screen"),
                          height=38, corner_radius=8,
                          fg_color=_BG, hover_color=_HOVER_BG,
                          text_color=_TEXT2, border_width=1, border_color=_BORDER,
                          font=ctk.CTkFont(size=12),
                          command=lambda: webbrowser.open("http://localhost:8000"),
                          state="disabled"),
            fg_color="BG", hover_color="HOVER_BG", text_color="TEXT2", border_color="BORDER",
        )
        self._browser_btn.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self._dyn.append((self._browser_btn, "open_screen"))

        self._start_btn = ctk.CTkButton(
            btn_bar, text=t("start_service"),
            height=38, corner_radius=8,
            fg_color=_ACCENT, hover_color=_ACCENT_HV,
            text_color="#ffffff",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._toggle,
        )
        self._start_btn.grid(row=0, column=2, sticky="ew")

    def _build_body(self) -> None:
        body = self._r(
            ctk.CTkScrollableFrame(self, fg_color=_BG, corner_radius=0,
                                   scrollbar_button_color=_BORDER,
                                   scrollbar_button_hover_color=_TEXT3),
            fg_color="BG", scrollbar_button_color="BORDER",
            scrollbar_button_hover_color="TEXT3",
        )
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        wrap = ctk.CTkFrame(body, fg_color="transparent")
        wrap.pack(fill="x", padx=28, pady=(20, 28))

        # ── Gateway (full width, top) ──────────────────────────────────────
        self._sec_label(wrap, "sec_gateway")
        gw = self._card(wrap)

        self._row_label(gw, 0, "room_name")
        self._room_entry = self._entry(gw, self._room_var)
        self._room_entry.grid(row=0, column=1, sticky="ew", padx=(0, 20), pady=9)

        self._row_label(gw, 1, "api_key")
        self._api_entry = self._entry(gw, self._api_var, show="*",
                                      placeholder="sk-xxxxxxxxxxxxxxxxxxxx")
        self._api_entry.grid(row=1, column=1, sticky="ew", padx=(0, 20), pady=9)

        self._row_label(gw, 2, "monitor_ip")
        self._monitor_entry = self._entry(gw, self._monitor_var,
                                          placeholder="Optional — e.g. 192.168.1.10")
        self._monitor_entry.grid(row=2, column=1, sticky="ew", padx=(0, 20), pady=9)

        # ── Display | Audio (40 / 60) ──────────────────────────────────────
        split = ctk.CTkFrame(wrap, fg_color="transparent")
        split.pack(fill="x")
        split.columnconfigure(0, weight=2)   # Display — 40 %
        split.columnconfigure(1, weight=3)   # Audio   — 60 %

        # Left column — Display (40 %)
        left_col = ctk.CTkFrame(split, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._sec_label(left_col, "sec_display")
        disp = self._card_bare(left_col)
        disp.pack(fill="x")

        LW = 106   # label width for the narrower column

        self._row_label(disp, 0, "mode", lw=LW)
        self._display_menu = self._menu(
            disp, self._display_var,
            ["Translated only", "Original only", "Both"],
            row=0,
        )

        self._row_label(disp, 1, "orig_size", lw=LW)
        self._zh_size_entry = self._px_entry(disp, self._zh_size_var, 1)

        self._row_label(disp, 2, "trans_size", lw=LW)
        self._en_size_entry = self._px_entry(disp, self._en_size_var, 2)

        self._row_label(disp, 3, "orig_color", lw=LW)
        self._zh_color_menu = self._menu(
            disp, self._zh_color_var, list(_COLORS.keys()), row=3,
        )

        self._row_label(disp, 4, "trans_color", lw=LW)
        self._en_color_menu = self._menu(
            disp, self._en_color_var, list(_COLORS.keys()), row=4,
        )

        self._row_label(disp, 5, "background", lw=LW)
        self._bg_menu = self._menu(
            disp, self._bg_var, list(_BG_COLORS.keys()),
            row=5, pady=(9, 14),
        )

        # Right column — Audio (60 %)
        right_col = ctk.CTkFrame(split, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self._sec_label(right_col, "sec_audio")
        audio = self._card_bare(right_col)
        audio.pack(fill="x")

        # Mic row: bordered menu + refresh button side by side
        self._row_label(audio, 0, "microphone", lw=96)
        mic_row = ctk.CTkFrame(audio, fg_color="transparent")
        mic_row.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=9)
        mic_row.columnconfigure(0, weight=1)

        mic_border = self._r(ctk.CTkFrame(mic_row, fg_color=_BORDER, corner_radius=9),
                             fg_color="BORDER")
        mic_border.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        mic_border.columnconfigure(0, weight=1)
        self._mic_menu = self._r(
            ctk.CTkOptionMenu(mic_border, variable=self._mic_var,
                              values=["Scanning..."], **self._om(),
                              dynamic_resizing=False),
            fg_color="SURFACE", button_color="ACCENT", button_hover_color="ACCENT_HV",
            text_color="TEXT", dropdown_fg_color="SURFACE",
            dropdown_text_color="TEXT", dropdown_hover_color="ACCENT_LT",
        )
        self._mic_menu.grid(row=0, column=0, sticky="ew", padx=1, pady=1)

        self._mic_refresh_btn = self._r(
            ctk.CTkButton(mic_row, text="↻", width=34, height=34,
                          fg_color=_BG, hover_color=_HOVER_BG,
                          text_color=_TEXT2, border_width=1, border_color=_BORDER,
                          corner_radius=8, font=ctk.CTkFont(size=15),
                          command=self._refresh_mics),
            fg_color="BG", hover_color="HOVER_BG",
            text_color="TEXT2", border_color="BORDER",
        )
        self._mic_refresh_btn.grid(row=0, column=1)

        self._row_label(audio, 1, "lang_pair", lw=96)
        self._lang_menu = self._menu(
            audio, self._lang_var,
            ["Chinese ↔ English", "Chinese ↔ Japanese"],
            row=1, pady=(9, 14),
        )

        # ── ASR Model (right column, below Audio) ─────────────────────────
        self._sec_label(right_col, "sec_asr")
        asr = self._card_bare(right_col)
        asr.pack(fill="x")

        self._row_label(asr, 0, "asr_model", lw=96)
        self._asr_menu = self._menu(
            asr, self._asr_var,
            ["paraformer-realtime-v2",
             "qwen3-asr-flash-realtime-2026-02-10",
             "fun-asr-realtime-2026-02-28"],
            row=0, pady=(9, 14), dynamic_resizing=True,
        )

        # ── Translation Model (right column, below ASR) ───────────────────
        self._sec_label(right_col, "sec_translate")
        trans = self._card_bare(right_col)
        trans.pack(fill="x")

        self._row_label(trans, 0, "translate_model", lw=96)
        self._translate_menu = self._menu(
            trans, self._translate_var,
            ["qwen-turbo", "qwen-plus", "qwen-max"],
            row=0, pady=(9, 14),
        )

        # All widgets that get disabled while running
        self._form_widgets = [
            self._mic_menu, self._mic_refresh_btn, self._lang_menu,
            self._asr_menu, self._translate_menu,
            self._room_entry, self._api_entry, self._monitor_entry,
            self._display_menu, self._zh_size_entry, self._en_size_entry,
            self._zh_color_menu, self._en_color_menu, self._bg_menu,
            self._load_btn,
        ]

    # ── Widget factory helpers ─────────────────────────────────────────────────

    def _sec_label(self, parent, key: str) -> ctk.CTkLabel:
        lbl = self._r(ctk.CTkLabel(parent, text=t(key), anchor="w",
                                   font=ctk.CTkFont(size=10, weight="bold"),
                                   text_color=_TEXT3),
                      text_color="TEXT3")
        lbl.pack(fill="x", pady=(18, 5), padx=2)
        self._dyn.append((lbl, key))
        return lbl

    def _card(self, parent) -> ctk.CTkFrame:
        card = self._r(ctk.CTkFrame(parent, fg_color=_SURFACE, corner_radius=12,
                                    border_width=1, border_color=_BORDER),
                       fg_color="SURFACE", border_color="BORDER")
        card.pack(fill="x")
        card.columnconfigure(1, weight=1)
        return card

    def _card_bare(self, parent) -> ctk.CTkFrame:
        card = self._r(ctk.CTkFrame(parent, fg_color=_SURFACE, corner_radius=12,
                                    border_width=1, border_color=_BORDER),
                       fg_color="SURFACE", border_color="BORDER")
        card.columnconfigure(1, weight=1)
        return card

    def _row_label(self, card, row: int, key: str, lw: int = 124) -> ctk.CTkLabel:
        lbl = self._r(ctk.CTkLabel(card, text=t(key), anchor="w", width=lw,
                                   font=ctk.CTkFont(size=12), text_color=_TEXT2),
                      text_color="TEXT2")
        lbl.grid(row=row, column=0, sticky="w", padx=(16, 10), pady=9)
        self._dyn.append((lbl, key))
        return lbl

    def _px_entry(self, card, var: ctk.StringVar, row: int) -> ctk.CTkEntry:
        f = ctk.CTkFrame(card, fg_color="transparent")
        f.grid(row=row, column=1, sticky="w", padx=(0, 16), pady=9)
        e = self._r(ctk.CTkEntry(f, textvariable=var, width=58, height=34,
                                 fg_color=_SURFACE, border_color=_BORDER,
                                 text_color=_TEXT, corner_radius=8),
                    fg_color="SURFACE", border_color="BORDER", text_color="TEXT")
        e.pack(side="left")
        self._r(ctk.CTkLabel(f, text=" px", font=ctk.CTkFont(size=11),
                             text_color=_TEXT3),
                text_color="TEXT3").pack(side="left")
        return e

    def _entry(self, parent, var, show="", placeholder="") -> ctk.CTkEntry:
        e = ctk.CTkEntry(parent, textvariable=var, show=show,
                         placeholder_text=placeholder, height=34,
                         fg_color=_SURFACE, border_color=_BORDER,
                         text_color=_TEXT, corner_radius=8)
        self._r(e, fg_color="SURFACE", border_color="BORDER", text_color="TEXT")
        return e

    def _om(self) -> dict:
        return dict(
            fg_color=_SURFACE, button_color=_ACCENT,
            button_hover_color=_ACCENT_HV, text_color=_TEXT,
            dropdown_fg_color=_SURFACE, dropdown_text_color=_TEXT,
            dropdown_hover_color=_ACCENT_LT, corner_radius=7,
            height=32,
        )

    def _menu(self, parent, var: ctk.StringVar, values: list,
              row: int, col: int = 1, padx: tuple = (0, 16),
              pady: int = 9, dynamic_resizing: bool = False,
              width: int = 0) -> ctk.CTkOptionMenu:
        border = self._r(ctk.CTkFrame(parent, fg_color=_BORDER, corner_radius=9),
                         fg_color="BORDER")
        border.grid(row=row, column=col, sticky="ew", padx=padx, pady=pady)
        border.columnconfigure(0, weight=1)
        kw = dict(**self._om(), dynamic_resizing=dynamic_resizing)
        if width:
            kw["width"] = width
        m = self._r(ctk.CTkOptionMenu(border, variable=var, values=values, **kw),
                    fg_color="SURFACE", button_color="ACCENT",
                    button_hover_color="ACCENT_HV", text_color="TEXT",
                    dropdown_fg_color="SURFACE", dropdown_text_color="TEXT",
                    dropdown_hover_color="ACCENT_LT")
        m.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        return m

    # ── Language update ────────────────────────────────────────────────────────

    def _apply_lang(self) -> None:
        for widget, key in self._dyn:
            widget.configure(text=t(key))
        # Status label reflects current running state
        self._status_lbl.configure(text=t(self._status_key))
        # Start/stop button text depends on runner state
        if self._runner.running:
            self._start_btn.configure(text=t("stop_service"))
        else:
            self._start_btn.configure(text=t("start_service"))

    # ── Microphone helpers ────────────────────────────────────────────────────

    def _refresh_mics(self) -> None:
        devices: list[tuple[int | None, str]] = []

        # ── Primary path: Windows IMMDeviceEnumerator ─────────────────────────
        # Enumerate exactly the devices Windows Sound Settings shows, then look
        # up each device's PyAudio index separately (three-pass name matching).
        active_names, default_name = _win_active_mics()
        if active_names and _PYAUDIO_OK:
            try:
                p = pyaudio.PyAudio()
                wasapi_api: int | None = None
                for h in range(p.get_host_api_count()):
                    if "WASAPI" in p.get_host_api_info_by_index(h).get("name", ""):
                        wasapi_api = h
                        break

                wasapi_devs: list[tuple[int, str]] = [
                    (i, info["name"])
                    for i in range(p.get_device_count())
                    if int((info := p.get_device_info_by_index(i))["maxInputChannels"]) > 0
                    and (wasapi_api is None or info["hostApi"] == wasapi_api)
                ]
                p.terminate()

                used: set[int] = set()

                def _find_idx(win_name: str) -> int | None:
                    wl = win_name.lower()
                    wb = wl.split("(")[0].strip()
                    for test in (
                        lambda pl: pl == wl,                               # exact
                        lambda pl: pl.startswith(wl) or wl.startswith(pl),# one is prefix of other
                        lambda pl: pl.split("(")[0].strip() == wb,         # base name only
                    ):
                        for idx, pyname in wasapi_devs:
                            if idx not in used and test(pyname.lower()):
                                used.add(idx)
                                return idx
                    return None

                for win_name in active_names:
                    devices.append((_find_idx(win_name), win_name))

                # Put default mic first
                if default_name:
                    dl = default_name.lower()
                    for i, (_, name) in enumerate(devices):
                        if name.lower() == dl:
                            if i != 0:
                                devices.insert(0, devices.pop(i))
                            break

            except Exception:
                pass

        # ── Fallback: PyAudio WASAPI (non-Windows or COM failure) ─────────────
        if not devices and _PYAUDIO_OK:
            try:
                p = pyaudio.PyAudio()
                wasapi_api = None
                for h in range(p.get_host_api_count()):
                    if "WASAPI" in p.get_host_api_info_by_index(h).get("name", ""):
                        wasapi_api = h
                        break
                seen: dict[str, tuple[int, str]] = {}
                for i in range(p.get_device_count()):
                    info = p.get_device_info_by_index(i)
                    if int(info["maxInputChannels"]) > 0:
                        if wasapi_api is None or info["hostApi"] == wasapi_api:
                            key = info["name"].strip().lower()
                            if key not in seen:
                                seen[key] = (i, info["name"])
                p.terminate()
                devices = list(seen.values())
            except Exception:
                pass

        self._mic_devices = devices
        names = [name for _, name in devices] or ["(No microphone detected)"]
        self._mic_menu.configure(values=names)
        self._mic_var.set(names[0])

    def _selected_index(self) -> int | None:
        val = self._mic_var.get()
        for i, name in self._mic_devices:
            if name == val:
                return i
        return None

    # ── Start / Stop ──────────────────────────────────────────────────────────

    def _toggle(self) -> None:
        if self._runner.running:
            self._stop()
        else:
            self._start()

    def _lang_pair_code(self) -> str:
        return "zh-ja" if "Japanese" in self._lang_var.get() else "zh-en"

    def _display_mode_code(self) -> str:
        val = self._display_var.get()
        if val == "Original only": return "zh"
        if val == "Both":          return "both"
        return "en"

    def _safe_size(self, var: ctk.StringVar, default: int) -> int:
        try:
            v = int(var.get())
            return max(12, min(v, 200))
        except ValueError:
            return default

    def _set_form_state(self, state: str) -> None:
        for w in self._form_widgets:
            try:
                w.configure(state=state)
            except Exception:
                pass

    def _start(self) -> None:
        self._save_settings()
        monitor_ip = self._monitor_var.get().strip() or None
        self._runner.start(
            self._selected_index(),
            api_key=self._api_var.get().strip(),
            lang_pair=self._lang_pair_code(),
            display_mode=self._display_mode_code(),
            zh_size=self._safe_size(self._zh_size_var, 56),
            en_size=self._safe_size(self._en_size_var, 40),
            zh_color=_COLORS[self._zh_color_var.get()],
            en_color=_COLORS[self._en_color_var.get()],
            bg_color=_BG_COLORS[self._bg_var.get()],
            asr_model=self._asr_var.get(),
            translate_model=self._translate_var.get(),
        )
        self._health_stop.clear()
        threading.Thread(target=self._poll_health, daemon=True, name="health-poll").start()
        self._sender.start(self._room_var.get(), self._get_status, target_ip=monitor_ip)

        self._start_btn.configure(
            text=t("stop_service"),
            fg_color=_STOP_BG, hover_color=_STOP_HV, text_color=_STOP_TEXT,
        )
        self._browser_btn.configure(state="normal")
        self._status_key = "status_starting"
        self._status_lbl.configure(text=t("status_starting"), text_color="#f59e0b")
        self._set_form_state("disabled")

    def _stop(self) -> None:
        self._runner.stop()
        self._health_stop.set()
        self._sender.stop()
        self._health = {}

        self._start_btn.configure(
            text=t("start_service"),
            fg_color=_ACCENT, hover_color=_ACCENT_HV, text_color="#ffffff",
        )
        self._browser_btn.configure(state="disabled")
        self._status_key = "status_stopped"
        self._status_lbl.configure(text=t("status_stopped"), text_color=_TEXT3)
        self._set_form_state("normal")

    # ── Health polling ────────────────────────────────────────────────────────

    def _poll_health(self) -> None:
        time.sleep(4)
        failures = 0
        while not self._health_stop.is_set() and self._runner.running:
            try:
                with urllib.request.urlopen("http://localhost:8000/health", timeout=2) as r:
                    self._health = json.loads(r.read())
                failures = 0
                self._status_key = "status_running"
                self.after(0, lambda: self._status_lbl.configure(
                    text=t("status_running"), text_color="#16a34a"))
            except Exception:
                self._health = {}
                failures += 1
                if failures >= 2:
                    self._status_key = "status_no_gw"
                    self.after(0, lambda: self._status_lbl.configure(
                        text=t("status_no_gw"), text_color="#dc2626"))
            self._health_stop.wait(5)

    def _get_status(self) -> dict:
        return {
            "status": "ok" if self._runner.running else "stopped",
            "ws_clients": self._health.get("screen_clients", 0),
            "terms_version": self._health.get("terms_version", 0),
        }

    # ── Settings persistence ──────────────────────────────────────────────────

    def _save_settings(self) -> None:
        # Save mic by name (not index) — indices shift when devices are
        # plugged/unplugged, but the name stays stable across sessions.
        # Read existing file first to preserve keys owned by other views (e.g. app_theme).
        try:
            existing = json.loads(_settings_path().read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        existing.update({
            "room":       self._room_var.get(),
            "api_key":    self._api_var.get(),
            "lang":       self._lang_var.get(),
            "mic":        self._mic_var.get(),
            "monitor_ip": self._monitor_var.get(),
            "display":    self._display_var.get(),
            "zh_size":    self._zh_size_var.get(),
            "en_size":    self._en_size_var.get(),
            "zh_color":   self._zh_color_var.get(),
            "en_color":   self._en_color_var.get(),
            "bg":         self._bg_var.get(),
            "asr_model":       self._asr_var.get(),
            "translate_model": self._translate_var.get(),
        })
        try:
            _settings_path().write_text(json.dumps(existing, indent=2), encoding="utf-8")
            self._load_btn.configure(state="normal")
        except Exception:
            pass

    def _apply_saved_settings(self) -> None:
        try:
            data = json.loads(_settings_path().read_text(encoding="utf-8"))
        except Exception:
            return
        self._room_var.set(data.get("room", "Room 1"))
        self._api_var.set(data.get("api_key", ""))
        self._lang_var.set(data.get("lang", "Chinese ↔ English"))
        self._monitor_var.set(data.get("monitor_ip", ""))
        self._display_var.set(data.get("display", "Both"))
        self._zh_size_var.set(data.get("zh_size", "30"))
        self._en_size_var.set(data.get("en_size", "30"))
        self._zh_color_var.set(data.get("zh_color", "Blue"))
        self._en_color_var.set(data.get("en_color", "Green"))
        self._bg_var.set(data.get("bg", "Black"))
        self._asr_var.set(data.get("asr_model", "qwen3-asr-flash-realtime-2026-02-10"))
        self._translate_var.set(data.get("translate_model", "qwen-plus"))

        # Restore mic by name — exact match first, then fuzzy substring fallback
        saved_mic = data.get("mic", "")
        if saved_mic and self._mic_devices:
            for _, name in self._mic_devices:
                if name == saved_mic:
                    self._mic_var.set(name)
                    break
            else:
                for _, name in self._mic_devices:
                    if saved_mic in name or name in saved_mic:
                        self._mic_var.set(name)
                        break

    # ── on_show sync ──────────────────────────────────────────────────────────

    def on_show(self) -> None:
        """Called when this view is brought to front via sidebar nav."""
        if self._runner.running:
            self._start_btn.configure(
                text=t("stop_service"),
                fg_color=_STOP_BG, hover_color=_STOP_HV, text_color=_STOP_TEXT,
            )
            self._browser_btn.configure(state="normal")
        else:
            self._start_btn.configure(
                text=t("start_service"),
                fg_color=_ACCENT, hover_color=_ACCENT_HV, text_color="#ffffff",
            )
            self._browser_btn.configure(state="disabled")


# Backward-compat alias (used by any code that imports ServiceWindow)
ServiceWindow = ServiceView
