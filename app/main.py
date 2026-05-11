"""
Entry point — run with:   python -m app
                       or  python app/main.py
"""
import customtkinter as ctk
from app.launcher import LauncherWindow


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.withdraw()          # hidden root; all UI lives in Toplevel windows

    LauncherWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
