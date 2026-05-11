import sys
import traceback
from pathlib import Path


def _error_log_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "error.log"
    return Path(__file__).parent.parent / "error.log"


def _run_as_gateway() -> None:
    """
    Gateway subprocess mode.
    Launched by runner.py when frozen:  AIInterpretation.exe --gateway <idx|none>
    """
    import os
    from dotenv import load_dotenv

    device_arg = sys.argv[2] if len(sys.argv) > 2 else "none"
    if device_arg != "none":
        os.environ["PYAUDIO_DEVICE_INDEX"] = device_arg

    # PyInstaller 6: bundled datas are in sys._MEIPASS (_internal/)
    if getattr(sys, "frozen", False):
        meipass = Path(sys._MEIPASS)
    else:
        meipass = Path(__file__).parent.parent

    load_dotenv(meipass / "gateway" / ".env", override=False)

    import gateway.main as gw
    import uvicorn
    uvicorn.run(gw.app, host="0.0.0.0", port=gw.PORT, reload=False)


def _run_as_ui() -> None:
    import customtkinter as ctk
    from app.launcher import LauncherWindow

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.withdraw()
    LauncherWindow(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--gateway":
            _run_as_gateway()
        else:
            _run_as_ui()
    except Exception:
        with open(_error_log_path(), "a") as f:
            traceback.print_exc(file=f)
        raise
