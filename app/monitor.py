import time

import customtkinter as ctk

from app import icon
from app.heartbeat import HeartbeatReceiver, HEARTBEAT_TIMEOUT

COLS = 4
CARD_W = 180


class MonitorWindow(ctk.CTkToplevel):
    """Monitor mode: live dashboard of all service laptops on the LAN."""

    def __init__(self, root: ctk.CTk, launcher):
        super().__init__(root)
        self.root = root
        self.launcher = launcher
        self.title("AI Interpretation — Monitor Center")
        self.geometry("860x580")
        self.minsize(640, 400)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._rooms: dict[str, dict] = {}
        self._cards: dict[str, dict] = {}

        self._receiver = HeartbeatReceiver(self._on_heartbeat)
        self._receiver.start()

        self._build()
        self._center()
        self._tick()
        icon.apply(self)
        self.lift()
        self.focus_force()

    def _center(self) -> None:
        self.update_idletasks()
        w, h = 860, 580
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(
            header, text="🖥  Monitor Center",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left")
        self._summary_lbl = ctk.CTkLabel(
            header, text="Waiting for heartbeats...",
            font=ctk.CTkFont(size=13), text_color="gray",
        )
        self._summary_lbl.pack(side="right")

        self._grid = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._grid.pack(fill="both", expand=True, padx=24, pady=(0, 4))
        for c in range(COLS):
            self._grid.columnconfigure(c, weight=1, minsize=CARD_W)

        self._empty_lbl = ctk.CTkLabel(
            self._grid,
            text="No rooms detected yet\n\nMake sure service laptops are on the same network and have started the service",
            font=ctk.CTkFont(size=13), text_color="gray",
        )
        self._empty_lbl.grid(row=0, column=0, columnspan=COLS, pady=60)

        ctk.CTkLabel(
            self, text="Updates every 3s  ·  Rooms silent for 15s+ are flagged as offline",
            font=ctk.CTkFont(size=11), text_color="gray",
        ).pack(pady=(0, 4))
        ctk.CTkButton(
            self, text="← Back",
            fg_color="transparent", hover_color="#374151",
            command=self._back,
        ).pack(pady=(0, 12))

    # ── Heartbeat callback ────────────────────────────────────────────────────

    def _on_heartbeat(self, payload: dict) -> None:
        self.after(0, self._apply_heartbeat, payload)

    def _apply_heartbeat(self, payload: dict) -> None:
        room = payload.get("room") or payload.get("ip", "Unknown")
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

    # ── Card management ───────────────────────────────────────────────────────

    def _add_card(self, room: str) -> None:
        idx = len(self._cards)
        row, col = divmod(idx, COLS)

        frame = ctk.CTkFrame(self._grid, corner_radius=12)
        frame.grid(row=row + 1, column=col, padx=6, pady=6, sticky="nsew")

        dot = ctk.CTkLabel(frame, text="●", font=ctk.CTkFont(size=22), text_color="#4ade80")
        dot.pack(pady=(16, 2))

        name_lbl = ctk.CTkLabel(frame, text=room, font=ctk.CTkFont(size=13, weight="bold"))
        name_lbl.pack()

        ip_lbl = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=11), text_color="gray")
        ip_lbl.pack()

        detail_lbl = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=11), text_color="gray")
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
            color = "#f87171"
            detail = f"⚠  No response ({int(age)}s)"
        elif info["status"] != "ok":
            color = "#facc15"
            detail = f"⚠  {info['status']}"
        else:
            color = "#4ade80"
            detail = f"Screen: {info['ws_clients']}  ·  Terms v{info['terms_version']}"

        card["dot"].configure(text_color=color)
        card["ip"].configure(text=info["ip"])
        card["detail"].configure(text=detail)

    # ── Summary bar ───────────────────────────────────────────────────────────

    def _refresh_summary(self) -> None:
        total = len(self._rooms)
        if total == 0:
            self._summary_lbl.configure(text="Waiting for heartbeats...", text_color="gray")
            return
        problems = sum(
            1 for info in self._rooms.values()
            if time.time() - info["last_seen"] > HEARTBEAT_TIMEOUT or info["status"] != "ok"
        )
        ok = total - problems
        color = "#4ade80" if problems == 0 else "#f87171"
        self._summary_lbl.configure(
            text=f"OK: {ok}  ·  Issues: {problems}  ·  Total: {total}",
            text_color=color,
        )

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
