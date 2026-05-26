import subprocess
import sys
import time

import customtkinter as ctk

from app import icon
from app.heartbeat import HeartbeatReceiver, HEARTBEAT_PORT, HEARTBEAT_TIMEOUT, local_ip

# ── Theme ─────────────────────────────────────────────────────────────────────
_BG      = "#f5f0e8"
_SURFACE = "#ffffff"
_BLUE    = "#7dd3fc"
_BLUE_HV = "#38bdf8"
_TINT    = "#e0f2fe"
_TEXT    = "#1e293b"
_TEXT2   = "#64748b"
_BORDER  = "#e2d9cc"


def _try_open_firewall() -> None:
    """Best-effort: add a Windows Firewall inbound rule for the UDP heartbeat port."""
    if sys.platform != "win32":
        return
    try:
        kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "add", "rule",
             f"name=AIInterpretation-Monitor-UDP{HEARTBEAT_PORT}",
             "protocol=UDP", "dir=in",
             f"localport={HEARTBEAT_PORT}",
             "action=allow", "enable=yes"],
            capture_output=True, timeout=5, **kwargs,
        )
    except Exception:
        pass

COLS = 4
CARD_W = 180


class MonitorWindow(ctk.CTkToplevel):
    """Monitor mode: live dashboard of all service laptops on the LAN."""

    def __init__(self, root: ctk.CTk, launcher):
        super().__init__(root)
        self.root = root
        self.launcher = launcher
        self.title("AI Interpretation — Monitor Center")
        self.geometry("860x640")
        self.minsize(640, 440)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.configure(fg_color=_BG)

        self._rooms: dict[str, dict] = {}
        self._cards: dict[str, dict] = {}

        _try_open_firewall()
        self._receiver = HeartbeatReceiver(self._on_heartbeat)
        self._receiver.start()
        self.after(20000, self._check_firewall_warning)

        self._build()
        self._center()
        self._tick()
        icon.apply(self)
        self.lift()
        self.focus_force()

    def _center(self) -> None:
        self.update_idletasks()
        w, h = 860, 640
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # ── Build UI ───────────────────────────────────────────────────────────────

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(
            header, text="Monitor Center",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=_TEXT,
        ).pack(side="left")
        self._summary_lbl = ctk.CTkLabel(
            header, text="Waiting for heartbeats...",
            font=ctk.CTkFont(size=13), text_color=_TEXT2,
        )
        self._summary_lbl.pack(side="right")

        # IP info bar
        ip_bar = ctk.CTkFrame(self, fg_color=_TINT, corner_radius=10)
        ip_bar.pack(fill="x", padx=24, pady=(0, 12))
        ctk.CTkLabel(
            ip_bar, text="This computer's IP:",
            font=ctk.CTkFont(size=12), text_color=_TEXT2,
        ).pack(side="left", padx=(16, 6), pady=10)
        ctk.CTkLabel(
            ip_bar, text=local_ip(),
            font=ctk.CTkFont(size=14, weight="bold"), text_color=_TEXT,
        ).pack(side="left", pady=10)
        ctk.CTkLabel(
            ip_bar,
            text="  ← Enter this into each Subtitle Service computer's Monitor IP field",
            font=ctk.CTkFont(size=11), text_color=_TEXT2,
        ).pack(side="left", pady=10)

        self._grid = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._grid.pack(fill="both", expand=True, padx=24, pady=(0, 4))
        for c in range(COLS):
            self._grid.columnconfigure(c, weight=1, minsize=CARD_W)

        self._empty_lbl = ctk.CTkLabel(
            self._grid,
            text="No rooms detected yet\n\nMake sure service laptops are on the same network and have started the service",
            font=ctk.CTkFont(size=13), text_color=_TEXT2, justify="center",
        )
        self._empty_lbl.grid(row=0, column=0, columnspan=COLS, pady=60)

        ctk.CTkLabel(
            self, text="Updates every 3s  ·  Rooms silent for 15s+ are flagged as offline",
            font=ctk.CTkFont(size=11), text_color=_TEXT2,
        ).pack(pady=(0, 4))
        ctk.CTkButton(
            self, text="← Back",
            fg_color="transparent", hover_color=_TINT, text_color=_TEXT2,
            command=self._back,
        ).pack(pady=(0, 12))

    # ── Heartbeat callback ────────────────────────────────────────────────────

    def _on_heartbeat(self, payload: dict) -> None:
        self.after(0, self._apply_heartbeat, payload)

    def _apply_heartbeat(self, payload: dict) -> None:
        room = payload.get("room") or payload.get("ip", "Unknown")
        if payload.get("status") == "stopped":
            self._remove_room(room)
            return
        self._rooms[room] = {
            "ip": payload.get("ip", ""),
            "status": payload.get("status", "ok"),
            "ws_clients": payload.get("ws_clients", 0),
            "terms_version": payload.get("terms_version", 0),
            "last_seen": payload.get("_received_at", time.time()),
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
                card["frame"].grid(row=r + 1, column=c, padx=6, pady=6, sticky="nsew")
        self._refresh_summary()
        if not self._rooms and self._empty_lbl.winfo_exists():
            self._empty_lbl.grid(row=0, column=0, columnspan=COLS, pady=60)

    # ── Card management ───────────────────────────────────────────────────────

    def _add_card(self, room: str) -> None:
        idx = len(self._cards)
        row, col = divmod(idx, COLS)

        frame = ctk.CTkFrame(
            self._grid, corner_radius=14,
            fg_color=_SURFACE, border_width=1, border_color=_BORDER,
        )
        frame.grid(row=row + 1, column=col, padx=6, pady=6, sticky="nsew")

        dot = ctk.CTkLabel(frame, text="●", font=ctk.CTkFont(size=22), text_color="#22c55e")
        dot.pack(pady=(16, 2))

        name_lbl = ctk.CTkLabel(
            frame, text=room,
            font=ctk.CTkFont(size=13, weight="bold"), text_color=_TEXT,
        )
        name_lbl.pack()

        ip_lbl = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=11), text_color=_TEXT2)
        ip_lbl.pack()

        detail_lbl = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=11), text_color=_TEXT2)
        detail_lbl.pack(pady=(2, 16))

        self._cards[room] = {
            "frame": frame, "dot": dot,
            "ip": ip_lbl, "detail": detail_lbl,
        }

    def _refresh_card(self, room: str) -> None:
        info = self._rooms[room]
        card = self._cards[room]
        age = time.time() - info["last_seen"]

        if age > HEARTBEAT_TIMEOUT:
            color = "#ef4444"
            detail = f"⚠  No response ({int(age)}s)"
        elif info["status"] != "ok":
            color = "#f59e0b"
            detail = f"⚠  {info['status']}"
        else:
            color = "#22c55e"
            detail = f"Screen: {info['ws_clients']}  ·  Terms v{info['terms_version']}"

        card["dot"].configure(text_color=color)
        card["ip"].configure(text=info["ip"])
        card["detail"].configure(text=detail)

    # ── Summary bar ───────────────────────────────────────────────────────────

    def _refresh_summary(self) -> None:
        total = len(self._rooms)
        if total == 0:
            self._summary_lbl.configure(text="Waiting for heartbeats...", text_color=_TEXT2)
            return
        problems = sum(
            1 for info in self._rooms.values()
            if time.time() - info["last_seen"] > HEARTBEAT_TIMEOUT or info["status"] != "ok"
        )
        ok = total - problems
        color = "#22c55e" if problems == 0 else "#ef4444"
        self._summary_lbl.configure(
            text=f"OK: {ok}  ·  Issues: {problems}  ·  Total: {total}",
            text_color=color,
        )

    # ── Firewall warning ──────────────────────────────────────────────────────

    def _check_firewall_warning(self) -> None:
        if len(self._rooms) == 0 and self._empty_lbl.winfo_ismapped():
            msg = (
                "No rooms detected yet\n\n"
                "If service laptops are running and on the same network,\n"
                "your firewall may be blocking UDP port 47474.\n\n"
            )
            if sys.platform == "win32":
                msg += "Fix: Run this app as Administrator once, or go to\nWindows Firewall → Allow an app → add AIInterpretation."
            else:
                msg += "Fix: Check macOS firewall settings under\nSystem Settings → Network → Firewall."
            self._empty_lbl.configure(text=msg, text_color="#f59e0b")

    # ── Tick ──────────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        for room in list(self._rooms):
            if room in self._cards:
                self._refresh_card(room)
        self._refresh_summary()
        self.after(3000, self._tick)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _back(self) -> None:
        self._receiver.stop()
        self.destroy()
        self.launcher.deiconify()

    def _on_close(self) -> None:
        self._receiver.stop()
        self.root.destroy()
