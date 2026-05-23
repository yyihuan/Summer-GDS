from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flask import Flask
from werkzeug.serving import BaseWSGIServer, make_server

from summer_gds.gui.desktop import PyWebviewSaveFileDialog
from summer_gds.gui.server import create_app
from summer_gds.gui.service import GuiSession


@dataclass
class LoopbackServerHandle:
    host: str
    port: int
    server: BaseWSGIServer
    thread: threading.Thread

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def stop(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()


def start_loopback_server(app: Flask, host: str = "127.0.0.1") -> LoopbackServerHandle:
    server = make_server(host, 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, name="summer-gds-gui-server", daemon=True)
    thread.start()
    return LoopbackServerHandle(host=host, port=server.server_port, server=server, thread=thread)


def launch_desktop(
    *,
    session_token: str | None = None,
    temp_root: Path | None = None,
    webview_module: Any | None = None,
) -> None:
    webview = webview_module or _import_webview()
    token = session_token or secrets.token_urlsafe(32)
    session = GuiSession(temp_root=temp_root)
    app = create_app(session_token=token, gui_session=session)
    handle = start_loopback_server(app)
    try:
        window = webview.create_window(
            "Summer GDS",
            handle.url,
            width=1280,
            height=720,
            min_size=(640, 360),
        )
        session.file_dialog = PyWebviewSaveFileDialog(window=window)
        webview.start()
    finally:
        handle.stop()
        session.close()


def main() -> int:
    launch_desktop()
    return 0


def _import_webview() -> Any:
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError("pywebview is required to launch the desktop GUI.") from exc
    return webview
