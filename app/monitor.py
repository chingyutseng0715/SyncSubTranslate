import subprocess
import sys
import time

import customtkinter as ctk

from app.heartbeat import HeartbeatReceiver, HEARTBEAT_PORT, HEARTBEAT_TIMEOUT, local_ip
from app.i18n import t, on_change

# ── Design tokens (keep in sync with launcher.py) ─────────────────────────────
_BG        = "#f5f6fa"
_SURFACE   = "#ffffff"
_ACCENT    = "#3b82f6"
_ACCENT_LT = "#eff6ff"
_TEXT      = "#111827"
_TEXT2     = "#6b7280"
_TEXT3     = "#9ca3af"
_BORDER    = "#e5e7eb"

_OK      = "#16a34a"
_WARN    = "#d97706"
_ERROR   = "#dc2626"
_OK_BG   = "#f0fdf4"
_WARN_BG = "#fffbeb"
_ERR_BG  = "#fef2f2"

COLS   = 3
CARD_W = 220


def _try_open_firewall() -> None:
    if sys.platform != "win32":
        return
    try:
        kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW}
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "add", "rule",
             f"name=AIInterpretation-Monitor-UDP{HEARTBEAT_PORT}",
             "protocol=UDP", "dir=in", f"localport={HEARTBEAT_PORT}",
             "action=allow", "enable=yes"],
            capture_output=True, timeout=5, **kwargs,
        )
    except Exception:
        pass


class MonitorView(ctk.CTkFrame):
    """Monitor mode: live dashboard of all Subtitle Service nodes on the LAN."""

    def __init__(self, parent, main_window):
        super().__init__(parent, fg_color=_BG, corner_radius=0)
        self.main_window = main_window

        self._rooms: dict[str, dict] = {}
        self._cards: dict[str, dict] = {}

        # i18n: (widget, key) pairs updated on language change
        self._dyn: list[tuple] = []

        # row 0 = header, row 1 = ip bar, row 2 = card grid (expands), row 3 = footer
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        _try_open_firewall()
        self._receiver = HeartbeatReceiver(self._on_heartbeat)
        self._receiver.start()
        self.after(20000, self._check_firewall_warning)

        self._build()
        self._tick()
        on_change(self._apply_lang)

    # ── Build UI ───────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # ── Header bar ────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=_SURFACE, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkFrame(hdr, height=1, fg_color=_BORDER).pack(side="bottom", fill="x")

        inner = ctk.CTkFrame(hdr, fg_color="transparent")
        inner.pack(fill="x", padx=28, pady=14)

        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left")

        title_lbl = ctk.CTkLabel(
            left, text=t("monitor_center"),
            font=ctk.CTkFont(size=18, weight="bold"), text_color=_TEXT,
        )
        title_lbl.pack(anchor="w")
        self._dyn.append((title_lbl, "monitor_center"))

        sub_lbl = ctk.CTkLabel(
            left, text=t("mon_subtitle"),
            font=ctk.CTkFont(size=11), text_color=_TEXT3,
        )
        sub_lbl.pack(anchor="w")
        self._dyn.append((sub_lbl, "mon_subtitle"))

        self._summary_lbl = ctk.CTkLabel(
            inner, text=t("waiting_hb"),
            font=ctk.CTkFont(size=12), text_color=_TEXT3,
        )
        self._summary_lbl.pack(side="right")

        # ── IP info bar ────────────────────────────────────────────────────
        ip_bar = ctk.CTkFrame(self, fg_color=_ACCENT_LT, corner_radius=0)
        ip_bar.grid(row=1, column=0, sticky="ew")
        ctk.CTkFrame(ip_bar, height=1, fg_color="#bfdbfe").pack(side="top", fill="x")
        ctk.CTkFrame(ip_bar, height=1, fg_color="#bfdbfe").pack(side="bottom", fill="x")

        ip_inner = ctk.CTkFrame(ip_bar, fg_color="transparent")
        ip_inner.pack(fill="x", padx=28, pady=10)

        ip_label = ctk.CTkLabel(
            ip_inner, text=t("this_ip"),
            font=ctk.CTkFont(size=12), text_color=_TEXT2,
        )
        ip_label.pack(side="left", padx=(0, 10))
        self._dyn.append((ip_label, "this_ip"))

        ip_chip = ctk.CTkFrame(
            ip_inner, fg_color=_SURFACE, corner_radius=6,
            border_width=1, border_color="#bfdbfe",
        )
        ip_chip.pack(side="left", padx=(0, 14))
        ctk.CTkLabel(
            ip_chip, text=f"  {local_ip()}  ",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=_ACCENT,
        ).pack(padx=2, pady=3)

        hint_lbl = ctk.CTkLabel(
            ip_inner, text=t("ip_hint"),
            font=ctk.CTkFont(size=11), text_color=_TEXT3,
        )
        hint_lbl.pack(side="left")
        self._dyn.append((hint_lbl, "ip_hint"))

        # ── Card grid ──────────────────────────────────────────────────────
        self._grid = ctk.CTkScrollableFrame(
            self, fg_color=_BG, corner_radius=0,
            scrollbar_button_color=_BORDER,
            scrollbar_button_hover_color=_TEXT3,
        )
        self._grid.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        for c in range(COLS):
            self._grid.columnconfigure(c, weight=1, minsize=CARD_W)

        self._empty_lbl = ctk.CTkLabel(
            self._grid,
            text="No rooms detected yet\n\nMake sure service laptops are on the same\nnetwork and have started the Subtitle Service",
            font=ctk.CTkFont(size=13), text_color=_TEXT3, justify="center",
        )
        self._empty_lbl.grid(row=0, column=0, columnspan=COLS, pady=80)

        # ── Footer ─────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color=_SURFACE, corner_radius=0)
        footer.grid(row=3, column=0, sticky="ew")
        ctk.CTkFrame(footer, height=1, fg_color=_BORDER).pack(side="top", fill="x")

        footer_lbl = ctk.CTkLabel(
            footer, text=t("footer_hint"),
            font=ctk.CTkFont(size=11), text_color=_TEXT3,
        )
        footer_lbl.pack(pady=10)
        self._dyn.append((footer_lbl, "footer_hint"))

    # ── Language update ────────────────────────────────────────────────────────

    def _apply_lang(self) -> None:
        for widget, key in self._dyn:
            widget.configure(text=t(key))
        # Summary label: only revert to idle text if no rooms are visible
        if len(self._rooms) == 0:
            self._summary_lbl.configure(text=t("waiting_hb"), text_color=_TEXT3)

    # ── Heartbeat callback ────────────────────────────────────────────────────

    def _on_heartbeat(self, payload: dict) -> None:
        self.after(0, self._apply_heartbeat, payload)

    def _apply_heartbeat(self, payload: dict) -> None:
        room = payload.get("room") or payload.get("ip", "Unknown")
        if payload.get("status") == "stopped":
            self._remove_room(room)
            return
        self._rooms[room] = {
            "ip":            payload.get("ip", ""),
            "status":        payload.get("status", "ok"),
            "ws_clients":    payload.get("ws_clients", 0),
            "terms_version": payload.get("terms_version", 0),
            "last_seen":     payload.get("_received_at", time.time()),
        }
        if room not in self._cards:
            self._add_card(room)
            if self._empty_lbl.winfo_ismapped():
                self._empty_lbl.grid_remove()
        self._refresh_card(room)
        self._refresh_summary()

    def _remove_room(self, room: str) -> None:
        self._rooms.pop(room, None)
        if room in self._cards:
            self._cards[room]["frame"].destroy()
            del self._cards[room]
            for idx, card in enumerate(self._cards.values()):
                r, c = divmod(idx, COLS)
                card["frame"].grid(row=r + 1, column=c, padx=8, pady=8, sticky="nsew")
        self._refresh_summary()
        if not self._rooms and self._empty_lbl.winfo_exists():
            self._empty_lbl.grid(row=0, column=0, columnspan=COLS, pady=80)

    # ── Card management ───────────────────────────────────────────────────────

    def _add_card(self, room: str) -> None:
        idx = len(self._cards)
        row, col = divmod(idx, COLS)

        frame = ctk.CTkFrame(
            self._grid, fg_color=_SURFACE, corner_radius=12,
            border_width=1, border_color=_BORDER,
        )
        frame.grid(row=row + 1, column=col, padx=8, pady=8, sticky="nsew")
        frame.columnconfigure(0, weight=1)

        # Coloured top accent stripe — updated with status colour in _refresh_card
        accent = ctk.CTkFrame(frame, height=4, corner_radius=0, fg_color=_OK)
        accent.grid(row=0, column=0, sticky="ew")

        # Card body
        body = ctk.CTkFrame(frame, fg_color="transparent")
        body.grid(row=1, column=0, sticky="ew", padx=18, pady=(12, 16))
        body.columnconfigure(1, weight=1)

        # Row 0: ● RoomName  [BADGE]
        dot = ctk.CTkLabel(body, text="●", font=ctk.CTkFont(size=12), text_color=_OK)
        dot.grid(row=0, column=0, sticky="w", padx=(0, 6))

        ctk.CTkLabel(
            body, text=room, anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=_TEXT,
        ).grid(row=0, column=1, sticky="w")

        badge = ctk.CTkLabel(
            body, text="RUNNING",
            font=ctk.CTkFont(size=9, weight="bold"),
            fg_color=_OK_BG, text_color=_OK, corner_radius=4,
        )
        badge.grid(row=0, column=2, sticky="e", padx=(8, 0))

        # Row 1: IP address
        ip_lbl = ctk.CTkLabel(
            body, text="", anchor="w",
            font=ctk.CTkFont(size=11), text_color=_TEXT3,
        )
        ip_lbl.grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

        # Row 2: screens + terms
        detail_lbl = ctk.CTkLabel(
            body, text="", anchor="w",
            font=ctk.CTkFont(size=11), text_color=_TEXT2,
        )
        detail_lbl.grid(row=2, column=0, columnspan=3, sticky="w", pady=(2, 0))

        self._cards[room] = {
            "frame":  frame,
            "accent": accent,
            "dot":    dot,
            "badge":  badge,
            "ip":     ip_lbl,
            "detail": detail_lbl,
        }

    def _refresh_card(self, room: str) -> None:
        info = self._rooms[room]
        card = self._cards[room]
        age = time.time() - info["last_seen"]

        if age > HEARTBEAT_TIMEOUT:
            color, bg = _ERROR, _ERR_BG
            badge_txt = "OFFLINE"
            detail = f"No response for {int(age)} s"
        elif info["status"] != "ok":
            color, bg = _WARN, _WARN_BG
            badge_txt = "ISSUE"
            detail = info["status"]
        else:
            color, bg = _OK, _OK_BG
            badge_txt = "RUNNING"
            screens = info["ws_clients"]
            detail = f"Screens: {screens}  ·  Terms v{info['terms_version']}"

        card["accent"].configure(fg_color=color)
        card["dot"].configure(text_color=color)
        card["badge"].configure(text=badge_txt, fg_color=bg, text_color=color)
        card["ip"].configure(text=info["ip"])
        card["detail"].configure(text=detail)

    # ── Summary bar ───────────────────────────────────────────────────────────

    def _refresh_summary(self) -> None:
        total = len(self._rooms)
        if total == 0:
            self._summary_lbl.configure(text=t("waiting_hb"), text_color=_TEXT3)
            return
        problems = sum(
            1 for info in self._rooms.values()
            if time.time() - info["last_seen"] > HEARTBEAT_TIMEOUT or info["status"] != "ok"
        )
        ok = total - problems
        if problems == 0:
            text = f"{ok} room{'s' if ok != 1 else ''} online"
            color = _OK
        else:
            text = f"{ok} online  ·  {problems} issue{'s' if problems != 1 else ''}"
            color = _ERROR
        self._summary_lbl.configure(text=text, text_color=color)

    # ── Firewall warning (20 s after init, if still empty) ───────────────────

    def _check_firewall_warning(self) -> None:
        if len(self._rooms) == 0 and self._empty_lbl.winfo_ismapped():
            msg = (
                "No rooms detected yet\n\n"
                "If service laptops are running and on the same network,\n"
                "your firewall may be blocking UDP port 47474.\n\n"
            )
            msg += (
                "Fix: Run this app as Administrator once, or allow it in\n"
                "Windows Firewall settings."
                if sys.platform == "win32" else
                "Fix: Check macOS firewall under System Settings → Network → Firewall."
            )
            self._empty_lbl.configure(text=msg, text_color=_WARN)

    # ── Tick (refresh cards every 3 s) ────────────────────────────────────────

    def _tick(self) -> None:
        for room in list(self._rooms):
            if room in self._cards:
                self._refresh_card(room)
        self._refresh_summary()
        self.after(3000, self._tick)

    def on_show(self) -> None:
        self._refresh_summary()


# Backward-compat alias
MonitorWindow = MonitorView
