from __future__ import annotations

import logging
import secrets
import sys
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Pre-warm matplotlib font cache and backends before anything else imports them.
# In a PyInstaller bundle the first import triggers a slow cache rebuild;
# doing it here avoids a confusing long pause.
import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager  # noqa: F401
import matplotlib.backends.backend_agg  # noqa: F401
import matplotlib.backends.backend_svg  # noqa: F401

from flask import Flask
from werkzeug.serving import BaseWSGIServer, make_server

from summer_gds.gui.desktop import PyWebviewSaveFileDialog
from summer_gds.gui.server import create_app
from summer_gds.gui.service import GuiSession

# Fatal-error log file for --windowed mode (no console visible).
_CRASH_LOG = Path.home() / ".summer-gds-crash.log"
_DEBUG_LOG = Path.home() / ".summer-gds-debug.log"


def _log(message: str) -> None:
    """Append to debug log so we can trace startup even in --windowed mode."""
    try:
        with open(_DEBUG_LOG, "a") as f:
            f.write(message + "\n")
    except OSError:
        pass


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
    _log("launch_desktop: start")
    webview = webview_module or _import_webview()
    _log("launch_desktop: webview imported, guilib=" + str(webview.guilib))

    # pywebview >= 6.x requires explicit initialization on some platforms.
    # If guilib is still None, call initialize() to force platform detection.
    if webview.guilib is None and hasattr(webview, "initialize"):
        _log("launch_desktop: calling webview.initialize()")
        webview.initialize()
        _log("launch_desktop: after initialize, guilib=" + str(webview.guilib))

    token = session_token or secrets.token_urlsafe(32)
    session = GuiSession(temp_root=temp_root)
    _log("launch_desktop: session created " + session.session_id)
    app = create_app(session_token=token, gui_session=session)
    _log("launch_desktop: Flask app created")
    handle = start_loopback_server(app)
    _log("launch_desktop: server at " + handle.url)
    try:
        window = webview.create_window(
            "Summer GDS",
            handle.url,
            width=1280,
            height=720,
            min_size=(640, 360),
        )
        session.file_dialog = PyWebviewSaveFileDialog(window=window)
        _log("launch_desktop: calling webview.start()")
        webview.start()
        _log("launch_desktop: webview.start() returned")
    finally:
        handle.stop()
        session.close()
        _log("launch_desktop: cleaned up")


def main() -> int:
    _log("=== Summer GDS starting === frozen=" + str(getattr(sys, "frozen", False)))
    try:
        launch_desktop()
    except Exception:
        _report_fatal(traceback.format_exc())
        return 1
    _log("=== Summer GDS exiting normally ===")
    return 0


def _report_fatal(message: str) -> None:
    """Write crash log and attempt a GUI error dialog so --windowed isn't silent."""
    logging.critical("Summer GDS fatal error:\n%s", message)
    _log("FATAL: " + message)
    try:
        sep = "=" * 40
        _CRASH_LOG.write_text(
            "Summer GDS crash report\n" + sep + "\n" + message + "\n"
        )
    except OSError:
        pass
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Summer GDS - Fatal Error",
            "Summer GDS failed to start.\n\n"
            "Details saved to:\n" + str(_CRASH_LOG) + "\n\n"
            + message[:500],
        )
        root.destroy()
    except Exception:
        pass


def _import_webview() -> Any:
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError("pywebview is required to launch the desktop GUI.") from exc
    return webview


if __name__ == "__main__":
    raise SystemExit(main())
