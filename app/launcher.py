import customtkinter as ctk
from app import icon

_BG      = "#f5f0e8"
_BLUE    = "#7dd3fc"
_BLUE_HV = "#38bdf8"
_TINT    = "#e0f2fe"
_TEXT    = "#1e293b"
_TEXT2   = "#64748b"


class LauncherWindow(ctk.CTkToplevel):
    """Role-selection screen shown on app launch."""

    def __init__(self, root: ctk.CTk):
        super().__init__(root)
        self.root = root
        self.title("AI Interpretation System")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", root.destroy)
        self.configure(fg_color=_BG)
        self._build()
        self._center(400, 290)
        icon.apply(self)
        self.lift()
        self.focus_force()

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="AI Interpretation",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=_TEXT,
        ).pack(pady=(44, 4))

        ctk.CTkLabel(
            self, text="Select the role for this computer",
            font=ctk.CTkFont(size=13),
            text_color=_TEXT2,
        ).pack(pady=(0, 32))

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=44)

        ctk.CTkButton(
            frame,
            text="Subtitle Service",
            height=52,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=_BLUE,
            hover_color=_BLUE_HV,
            text_color=_TEXT,
            corner_radius=10,
            command=self._go_service,
        ).pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            frame,
            text="Monitor Center",
            height=52,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=_TINT,
            hover_color=_BLUE,
            text_color=_TEXT,
            corner_radius=10,
            command=self._go_monitor,
        ).pack(fill="x")

    def _go_service(self) -> None:
        try:
            from app.service import ServiceWindow
        except Exception as e:
            import tkinter.messagebox as mb
            mb.showerror("Failed to open Subtitle Service", str(e))
            return
        self.withdraw()
        ServiceWindow(self.root, self)

    def _go_monitor(self) -> None:
        try:
            from app.monitor import MonitorWindow
        except Exception as e:
            import tkinter.messagebox as mb
            mb.showerror("Failed to open Monitor Center", str(e))
            return
        self.withdraw()
        try:
            MonitorWindow(self.root, self)
        except Exception as e:
            import tkinter.messagebox as mb
            self.deiconify()
            mb.showerror("Failed to open Monitor Center", str(e))
