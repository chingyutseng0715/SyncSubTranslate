"""Launches the translation gateway as a subprocess."""
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

BASE_DIR = Path(__file__).parent.parent
GATEWAY_SCRIPT = BASE_DIR / "gateway" / "main.py"
GATEWAY_PORT = 8000


def _release_port(port: int) -> None:
    """Force-kill any process still holding the given TCP port."""
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(
                ["netstat", "-ano"],
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            for line in out.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    if pid.isdigit() and int(pid) > 4:
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid],
                            capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        )
        except Exception:
            pass
    else:
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True, text=True,
            )
            for pid in result.stdout.split():
                if pid.strip().isdigit():
                    subprocess.run(["kill", "-9", pid.strip()], capture_output=True)
        except Exception:
            pass


class GatewayRunner:
    def __init__(self):
        self._proc: subprocess.Popen | None = None

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self, device_index: int | None, api_key: str = "", lang_pair: str = "zh-en",
              display_mode: str = "both", zh_size: int = 30, en_size: int = 30,
              zh_color: str = "#7dd3fc", en_color: str = "#4ade80",
              bg_color: str = "#000000",
              asr_model: str = "qwen3-asr-flash-realtime-2026-02-10",
              translate_model: str = "qwen-plus",
              on_line: Callable[[str], None] | None = None) -> None:
        if self.running:
            return
        _release_port(GATEWAY_PORT)  # evict any orphaned gateway from a prior session

        idx = str(device_index) if device_index is not None else "none"
        env = os.environ.copy()
        if api_key:
            env["DASHSCOPE_API_KEY"] = api_key
        env["LANG_PAIR"] = lang_pair
        env["DISPLAY_MODE"] = display_mode
        env["ZH_FONT_SIZE"] = str(zh_size)
        env["EN_FONT_SIZE"] = str(en_size)
        env["ZH_COLOR"] = zh_color
        env["EN_COLOR"] = en_color
        env["BG_COLOR"] = bg_color
        env["ASR_MODEL"] = asr_model
        env["TRANSLATE_MODEL"] = translate_model

        if getattr(sys, "frozen", False):
            # Bundled exe: relaunch self with --gateway flag
            cmd = [sys.executable, "--gateway", idx]
            # cwd = the _internal/gateway dir where bundled gateway files live
            cwd = str(Path(sys._MEIPASS) / "gateway")
            # Tell gateway where to write logs (user data dir, not beside the exe)
            from app.paths import user_data_dir
            env["AI_DATA_DIR"] = str(user_data_dir())
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
        _release_port(GATEWAY_PORT)  # catch zombies the subprocess kill may have missed

    def _stream(self, on_line: Callable[[str], None] | None) -> None:
        try:
            for line in self._proc.stdout:
                if on_line:
                    on_line(line.rstrip())
        except Exception:
            pass
