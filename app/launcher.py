import customtkinter as ctk
from app import icon


class LauncherWindow(ctk.CTkToplevel):
    """Role-selection screen shown on app launch."""

    def __init__(self, root: ctk.CTk):
        super().__init__(root)
        self.root = root
        self.title("AI Interpretation System")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", root.destroy)
        self._build()
        self._center(420, 320)
        icon.apply(self)
        self.lift()
        self.focus_force()

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="AI Interpretation System",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(pady=(40, 6))

        ctk.CTkLabel(
            self, text="Select the role for this computer",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        ).pack(pady=(0, 36))

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=48)

        ctk.CTkButton(
            frame,
            text="🎙   Subtitle Service",
            height=56,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._go_service,
        ).pack(fill="x", pady=(0, 14))

        ctk.CTkButton(
            frame,
            text="🖥   Monitor Center",
            height=56,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#1a4731",
            hover_color="#22603f",
            command=self._go_monitor,
        ).pack(fill="x")

    def _go_service(self) -> None:
        from app.service import ServiceWindow
        self.withdraw()
        ServiceWindow(self.root, self)

    def _go_monitor(self) -> None:
        from app.monitor import MonitorWindow
        self.withdraw()
        MonitorWindow(self.root, self)
