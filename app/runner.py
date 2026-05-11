"""Launches the translation gateway as a subprocess."""
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

BASE_DIR = Path(__file__).parent.parent
GATEWAY_SCRIPT = BASE_DIR / "gateway" / "main.py"


class GatewayRunner:
    def __init__(self):
        self._proc: subprocess.Popen | None = None

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self, device_index: int | None, api_key: str = "", lang_pair: str = "zh-en", on_line: Callable[[str], None] | None = None) -> None:
        if self.running:
            return

        idx = str(device_index) if device_index is not None else "none"
        env = os.environ.copy()
        if api_key:
            env["DASHSCOPE_API_KEY"] = api_key
        env["LANG_PAIR"] = lang_pair

        if getattr(sys, "frozen", False):
            # Bundled exe: relaunch self with --gateway flag
            cmd = [sys.executable, "--gateway", idx]
            # cwd = the _internal/gateway dir where bundled gateway files live
            cwd = str(Path(sys._MEIPASS) / "gateway")
        else:
            # Development: launch gateway/main.py directly
            if device_index is not None:
                env["PYAUDIO_DEVICE_INDEX"] = idx
            cmd = [sys.executable, str(GATEWAY_SCRIPT)]
            cwd = str(GATEWAY_SCRIPT.parent)

        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=cwd,
            **kwargs,
        )
        threading.Thread(
            target=self._stream, args=(on_line,), daemon=True, name="gw-log"
        ).start()

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    def _stream(self, on_line: Callable[[str], None] | None) -> None:
        try:
            for line in self._proc.stdout:
                if on_line:
                    on_line(line.rstrip())
        except Exception:
            pass
