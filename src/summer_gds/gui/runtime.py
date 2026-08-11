from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

from flask import Flask
from werkzeug.serving import BaseWSGIServer, make_server


READINESS_TIMEOUT_SECONDS = 5.0


class RequestGate:
    """Track authenticated API work and reject new work during shutdown."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._closing = False
        self._inflight = 0

    def try_enter(self) -> bool:
        with self._condition:
            if self._closing:
                return False
            self._inflight += 1
            return True

    def leave(self) -> None:
        with self._condition:
            assert self._inflight > 0, "RequestGate.leave() underflow"
            self._inflight -= 1
            if self._inflight == 0:
                self._condition.notify_all()

    def begin_shutdown(self) -> None:
        with self._condition:
            self._closing = True
            self._condition.notify_all()

    def wait_drained(self, timeout: float) -> bool:
        deadline = time.monotonic() + max(0.0, timeout)
        with self._condition:
            while self._inflight:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return True

    @property
    def inflight(self) -> int:
        with self._condition:
            return self._inflight


@dataclass
class LoopbackServerHandle:
    host: str
    port: int
    server: BaseWSGIServer
    thread: threading.Thread
    _stop_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _stopped: bool = field(default=False, init=False, repr=False)
    _server_closed: bool = field(default=False, init=False, repr=False)

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def shutdown(self) -> None:
        self.server.shutdown()

    def join(self, timeout: float) -> bool:
        self.thread.join(timeout=max(0.0, timeout))
        return not self.thread.is_alive()

    def server_close(self) -> None:
        with self._stop_lock:
            if self._server_closed:
                return
            self._server_closed = True
        self.server.server_close()

    def stop(self, timeout: float = 2.0) -> None:
        with self._stop_lock:
            if self._stopped:
                return
            self._stopped = True
        try:
            self.shutdown()
            self.join(timeout)
        finally:
            self.server_close()


def start_loopback_server(
    app: Flask,
    host: str = "127.0.0.1",
    *,
    readiness_timeout: float = READINESS_TIMEOUT_SECONDS,
) -> LoopbackServerHandle:
    server = make_server(host, 0, app, threaded=True)
    thread = threading.Thread(
        target=server.serve_forever,
        name="summer-gds-gui-server",
        daemon=True,
    )
    handle = LoopbackServerHandle(
        host=host,
        port=server.server_port,
        server=server,
        thread=thread,
    )
    thread.start()
    try:
        _wait_until_ready(handle.url, readiness_timeout)
    except Exception:
        handle.stop()
        raise
    return handle


def _wait_until_ready(url: str, timeout: float) -> None:
    deadline = time.monotonic() + max(0.0, timeout)
    opener = build_opener(ProxyHandler({}))
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with opener.open(url, timeout=min(0.5, max(0.05, deadline - time.monotonic()))) as response:
                html = response.read().decode("utf-8")
            if response.status == 200 and "Summer GDS" in html:
                return
            last_error = RuntimeError("loopback readiness response did not contain the application shell")
        except (OSError, URLError, UnicodeError) as exc:
            last_error = exc
        time.sleep(min(0.02, max(0.0, deadline - time.monotonic())))
    raise TimeoutError("Summer GDS loopback server did not become ready within the startup deadline") from last_error
