"""
UDP broadcast heartbeat — service laptops announce themselves every 5s.
Monitor laptop listens and tracks which rooms have gone silent.
"""
import json
import socket
import threading
import time
from typing import Callable

HEARTBEAT_PORT = 47474
HEARTBEAT_INTERVAL = 5   # seconds between broadcasts
HEARTBEAT_TIMEOUT = 15   # seconds before a room is marked as problem


def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class HeartbeatSender:
    """Runs on service laptops — broadcasts status every HEARTBEAT_INTERVAL seconds."""

    def __init__(self):
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, room: str, get_status: Callable[[], dict]) -> None:
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, args=(room, get_status), daemon=True, name="hb-sender"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self, room: str, get_status: Callable[[], dict]) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            while not self._stop.is_set():
                payload = {"room": room, "ip": _local_ip(), **get_status()}
                try:
                    sock.sendto(json.dumps(payload).encode(), ("255.255.255.255", HEARTBEAT_PORT))
                except Exception:
                    pass
                self._stop.wait(HEARTBEAT_INTERVAL)
            goodbye = {"room": room, "ip": _local_ip(), "status": "stopped", "ws_clients": 0, "terms_version": 0}
            try:
                sock.sendto(json.dumps(goodbye).encode(), ("255.255.255.255", HEARTBEAT_PORT))
            except Exception:
                pass
        finally:
            sock.close()


class HeartbeatReceiver:
    """Runs on the monitor laptop — collects broadcasts and calls callback for each."""

    def __init__(self, callback: Callable[[dict], None]):
        self._callback = callback
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="hb-receiver"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1.0)
        try:
            sock.bind(("", HEARTBEAT_PORT))
            while not self._stop.is_set():
                try:
                    data, addr = sock.recvfrom(2048)
                    payload = json.loads(data.decode())
                    payload.setdefault("ip", addr[0])
                    payload["_received_at"] = time.time()
                    self._callback(payload)
                except socket.timeout:
                    pass
                except Exception:
                    pass
        finally:
            sock.close()
