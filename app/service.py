import json
import threading
import time
import urllib.request
import webbrowser

import customtkinter as ctk
import pyaudio

from app import icon
from app.heartbeat import HeartbeatSender
from app.runner import GatewayRunner

_BTN_BLUE = ("#3B8ED0", "#1F6AA5")
_BTN_BLUE_HOVER = ("#36719F", "#144870")
_BTN_RED = ("#7f1d1d", "#7f1d1d")
_BTN_RED_HOVER = ("#991b1b", "#991b1b")


class ServiceWindow(ctk.CTkToplevel):
    """Service-mode window: mic picker, start/stop gateway."""

    def __init__(self, root: ctk.CTk, launcher):
        super().__init__(root)
        self.root = root
        self.launcher = launcher
        self.title("AI Interpretation — Subtitle Service")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._runner = GatewayRunner()
        self._sender = HeartbeatSender()
        self._mic_devices: list[tuple[int, str]] = []
        self._health: dict = {}
        self._health_stop = threading.Event()

        self._build()
        self._center(520, 390)
        self._refresh_mics()
        icon.apply(self)
        self.lift()
        self.focus_force()

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="🎙  Subtitle Service",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(24, 4))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=36, pady=8)
        form.columnconfigure(1, weight=1)

        # Room name
        ctk.CTkLabel(form, text="Room Name", anchor="w", width=100).grid(
            row=0, column=0, sticky="w", pady=8, padx=(0, 12)
        )
        self._room_var = ctk.StringVar(value="Room 1")
        self._room_entry = ctk.CTkEntry(form, textvariable=self._room_var)
        self._room_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=8)

        # API key
        ctk.CTkLabel(form, text="API Key", anchor="w", width=100).grid(
            row=1, column=0, sticky="w", pady=8, padx=(0, 12)
        )
        self._api_var = ctk.StringVar()
        self._api_entry = ctk.CTkEntry(form, textvariable=self._api_var, show="*",
                                       placeholder_text="sk-xxxxxxxxxxxxxxxxxxxx")
        self._api_entry.grid(row=1, column=1, columnspan=2, sticky="ew", pady=8)

        # Microphone
        ctk.CTkLabel(form, text="Microphone", anchor="w", width=100).grid(
            row=2, column=0, sticky="w", pady=8, padx=(0, 12)
        )
        self._mic_var = ctk.StringVar(value="Scanning...")
        self._mic_menu = ctk.CTkOptionMenu(
            form, variable=self._mic_var, values=["Scanning..."], dynamic_resizing=False
        )
        self._mic_menu.grid(row=2, column=1, sticky="ew", pady=8, padx=(0, 8))
        ctk.CTkButton(form, text="↻", width=36, command=self._refresh_mics).grid(row=2, column=2)

        # Action buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=36, pady=(12, 0))

        self._start_btn = ctk.CTkButton(
            btn_row, text="▶  Start Service", height=46,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._toggle,
        )
        self._start_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self._browser_btn = ctk.CTkButton(
            btn_row, text="🌐  Open Screen", height=46,
            fg_color="#374151", hover_color="#4b5563",
            command=lambda: webbrowser.open("http://localhost:8000"),
            state="disabled",
        )
        self._browser_btn.pack(side="left", expand=True, fill="x", padx=(6, 0))

        # Status indicator
        self._status_lbl = ctk.CTkLabel(
            self, text="● Not started", text_color="gray",
            font=ctk.CTkFont(size=13),
        )
        self._status_lbl.pack(pady=(16, 8))

        ctk.CTkButton(
            self, text="← Back",
            fg_color="transparent", hover_color="#374151",
            command=self._back,
        ).pack(pady=(0, 20))

    # ── Microphone helpers ────────────────────────────────────────────────────

    def _refresh_mics(self) -> None:
        devices: list[tuple[int, str]] = []
        try:
            p = pyaudio.PyAudio()
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if int(info["maxInputChannels"]) > 0:
                    devices.append((i, info["name"]))
            p.terminate()
        except Exception:
            pass
        self._mic_devices = devices
        names = [f"[{i}] {name}" for i, name in devices] or ["(No microphone detected)"]
        self._mic_menu.configure(values=names)
        self._mic_var.set(names[0])

    def _selected_index(self) -> int | None:
        val = self._mic_var.get()
        for i, _ in self._mic_devices:
            if val.startswith(f"[{i}]"):
                return i
        return None

    # ── Start / Stop ──────────────────────────────────────────────────────────

    def _toggle(self) -> None:
        if self._runner.running:
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        self._runner.start(self._selected_index(), api_key=self._api_var.get().strip())
        self._health_stop.clear()
        threading.Thread(target=self._poll_health, daemon=True, name="health-poll").start()
        self._sender.start(self._room_var.get(), self._get_status)
        self._start_btn.configure(text="⏹  Stop Service", fg_color=_BTN_RED, hover_color=_BTN_RED_HOVER)
        self._browser_btn.configure(state="normal")
        self._status_lbl.configure(text="● Starting...", text_color="#facc15")
        self._room_entry.configure(state="disabled")
        self._api_entry.configure(state="disabled")
        self._mic_menu.configure(state="disabled")

    def _stop(self) -> None:
        self._runner.stop()
        self._health_stop.set()
        self._sender.stop()
        self._health = {}
        self._start_btn.configure(text="▶  Start Service", fg_color=_BTN_BLUE, hover_color=_BTN_BLUE_HOVER)
        self._browser_btn.configure(state="disabled")
        self._status_lbl.configure(text="● Stopped", text_color="gray")
        self._room_entry.configure(state="normal")
        self._api_entry.configure(state="normal")
        self._mic_menu.configure(state="normal")

    # ── Health polling (for heartbeat payload) ────────────────────────────────

    def _poll_health(self) -> None:
        time.sleep(4)  # give gateway time to boot
        failures = 0
        while not self._health_stop.is_set() and self._runner.running:
            try:
                with urllib.request.urlopen("http://localhost:8000/health", timeout=2) as r:
                    self._health = json.loads(r.read())
                failures = 0
                self.after(0, lambda: self._status_lbl.configure(
                    text="● Running", text_color="#4ade80"))
            except Exception:
                self._health = {}
                failures += 1
                if failures >= 2:
                    self.after(0, lambda: self._status_lbl.configure(
                        text="● Gateway not responding", text_color="#f87171"))
            self._health_stop.wait(5)

    def _get_status(self) -> dict:
        return {
            "status": "ok" if self._runner.running else "stopped",
            "ws_clients": self._health.get("screen_clients", 0),
            "terms_version": self._health.get("terms_version", 0),
        }

    # ── Navigation ────────────────────────────────────────────────────────────

    def _back(self) -> None:
        self._stop()
        self.destroy()
        self.launcher.deiconify()

    def _on_close(self) -> None:
        self._stop()
        self.root.destroy()
