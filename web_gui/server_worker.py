"""WSGI 服务线程管理工具。

阶段 2 引入该模块，封装 Flask/Werkzeug 服务的启动与关闭逻辑，
以便后续 Qt 窗口与 CLI 模式共享相同的生命周期控制接口。
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from werkzeug.serving import make_server


LOGGER = logging.getLogger(__name__)


class ServerWorker:
    """在独立线程中运行 Flask 应用的辅助类。"""

    def __init__(self, app, host: str, port: int, debug: bool = False) -> None:
        self._app = app
        self._host = host
        self._port = port
        self._debug = debug

        self._server = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._stopped = threading.Event()

    @property
    def url(self) -> str:
        host = "localhost" if self._host == "0.0.0.0" else self._host
        return f"http://{host}:{self._port}"

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            raise RuntimeError("ServerWorker 已在运行状态")

        # 更新 Flask 应用调试标记，确保日志级别与配置一致。
        if hasattr(self._app, "debug"):
            self._app.debug = self._debug

        self._stopped.clear()
        self._server = make_server(
            self._host,
            self._port,
            self._app,
            threaded=True,
            passthrough_errors=True,
        )
        self._server.daemon_threads = True
        self._port = self._server.server_port

        self._thread = threading.Thread(
            target=self._serve,
            name="SummerGDS-WSGIServer",
            daemon=True,
        )
        self._thread.start()

    def wait_ready(self, timeout: Optional[float] = None) -> bool:
        return self._ready.wait(timeout)

    def shutdown(self, timeout: Optional[float] = 5.0) -> None:
        if self._server is None:
            return

        LOGGER.debug("Shutting down ServerWorker ...")
        try:
            self._server.shutdown()
        finally:
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout)

        self._server = None
        self._thread = None
        self._ready.clear()
        self._stopped.set()

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive() and not self._stopped.is_set())

    def _serve(self) -> None:
        try:
            LOGGER.debug("Starting WSGI serve_forever loop")
            self._ready.set()
            self._server.serve_forever()
        except Exception:  # pragma: no cover - 记录异常后继续抛出
            LOGGER.exception("WSGI 服务线程异常退出")
            raise
        finally:
            self._stopped.set()
