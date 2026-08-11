from __future__ import annotations

import logging
import os
import platform
import secrets
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMessageBox, QMainWindow

from summer_gds.gui.bundle_probe import (
    PROBE_TOTAL_TIMEOUT_SECONDS,
    BundleProbe,
    ProbeActivationError,
    activate_bundle_probe,
)
from summer_gds.gui.qt_dialog import QtSaveFileDialog
from summer_gds.gui.runtime import LoopbackServerHandle, RequestGate, start_loopback_server
from summer_gds.gui.server import create_app
from summer_gds.gui.service import GuiSession


SHUTDOWN_TIMEOUT_SECONDS = 10.0
DOM_READY_SCRIPT = """
(() => Boolean(
  document.querySelector('#app') &&
  document.querySelector('#workspace') &&
  window.SUMMER_GDS_APP_READY === true
))()
"""


class OriginInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, origin: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._origin = origin

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        url = info.requestUrl()
        if _origin(url) != self._origin:
            info.block(True)


class RestrictedPage(QWebEnginePage):
    fatal_error = Signal(str)

    def __init__(self, profile: QWebEngineProfile, origin: str, parent: QObject | None = None) -> None:
        super().__init__(profile, parent)
        self._origin = origin

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        if _origin(url) == self._origin:
            return True
        logging.warning("Blocked external navigation")
        return False

    def createWindow(self, window_type):
        logging.warning("Blocked new WebEngine window")
        return None

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        safe = str(message).replace("\n", " ")[:1000]
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel:
            logging.debug("Web UI: %s", safe)
        else:
            logging.warning("Web UI: %s", safe)


class ShellWindow(QMainWindow):
    close_requested = Signal()

    def closeEvent(self, event):
        event.ignore()
        self.setEnabled(False)
        self.hide()
        self.close_requested.emit()


@dataclass(frozen=True)
class ShutdownResult:
    server_stopped: bool
    request_gate_drained: bool
    server_closed: bool
    session_removed: bool
    error_stage: str | None = None

    @property
    def ok(self) -> bool:
        return all(
            (
                self.server_stopped,
                self.request_gate_drained,
                self.server_closed,
                self.session_removed,
            )
        )


class ShutdownCoordinator(QObject):
    worker_finished = Signal(object)

    def __init__(
        self,
        *,
        application: QApplication,
        window: QMainWindow,
        page: QWebEnginePage,
        profile: QWebEngineProfile,
        dialog: object,
        server: LoopbackServerHandle,
        gate: RequestGate,
        session: GuiSession,
        probe: BundleProbe | None,
        timeout: float = SHUTDOWN_TIMEOUT_SECONDS,
    ) -> None:
        super().__init__(application)
        self._application = application
        self._window = window
        self._page = page
        self._profile = profile
        self._dialog = dialog
        self._server = server
        self._gate = gate
        self._session = session
        self._probe = probe
        self._timeout = timeout
        self._lock = threading.Lock()
        self._state = "running"
        self._deadline = 0.0
        self._watchdog = QTimer(self)
        self._watchdog.setSingleShot(True)
        self._watchdog.timeout.connect(self._on_watchdog)
        self.worker_finished.connect(self._on_worker_finished)

    @Slot()
    def begin(self, error_stage: str | None = None) -> None:
        with self._lock:
            if self._state != "running":
                return
            self._state = "closing"
            self._deadline = time.monotonic() + self._timeout
        self._window.setEnabled(False)
        self._window.hide()
        begin_dialog_shutdown = getattr(self._dialog, "begin_shutdown", None)
        if begin_dialog_shutdown is not None:
            begin_dialog_shutdown()
        self._gate.begin_shutdown()
        self._watchdog.start(max(1, int(self._timeout * 1000)))
        thread = threading.Thread(
            target=self._shutdown_worker,
            args=(error_stage,),
            name="summer-gds-shutdown",
            daemon=True,
        )
        thread.start()

    def _shutdown_worker(self, requested_error: str | None) -> None:
        server_stopped = False
        drained = False
        server_closed = False
        session_removed = False
        error_stage = requested_error
        try:
            self._server.shutdown()
            server_stopped = self._server.join(self._remaining())
            if not server_stopped and error_stage is None:
                error_stage = "server_join_timeout"
            drained = self._gate.wait_drained(self._remaining())
            if not drained and error_stage is None:
                error_stage = "request_drain_timeout"
        finally:
            try:
                self._server.server_close()
                server_closed = True
            except Exception:
                if error_stage is None:
                    error_stage = "server_close_failed"

        with self._lock:
            may_clean = self._state == "closing" and server_stopped and drained
        if may_clean:
            try:
                self._session.close()
                session_removed = not self._session.session_dir.exists()
                if not session_removed and error_stage is None:
                    error_stage = "session_cleanup_failed"
            except Exception:
                if error_stage is None:
                    error_stage = "session_cleanup_failed"
        result = ShutdownResult(
            server_stopped=server_stopped,
            request_gate_drained=drained,
            server_closed=server_closed,
            session_removed=session_removed,
            error_stage=error_stage,
        )
        self.worker_finished.emit(result)

    def _remaining(self) -> float:
        return max(0.0, self._deadline - time.monotonic())

    @Slot(object)
    def _on_worker_finished(self, result: ShutdownResult) -> None:
        with self._lock:
            if self._state != "closing":
                return
            self._state = "finished" if result.ok and result.error_stage is None else "failed"
        self._watchdog.stop()
        self._finish(result, 0 if self._state == "finished" else 1)

    @Slot()
    def _on_watchdog(self) -> None:
        with self._lock:
            if self._state != "closing":
                return
            self._state = "timed_out"
        result = ShutdownResult(False, False, False, False, "server_join_timeout")
        self._finish(result, 1)

    def _finish(self, result: ShutdownResult, exit_code: int) -> None:
        if self._probe is not None:
            self._probe.publish_complete(
                pid=os.getpid(),
                result="ok" if exit_code == 0 else "failed",
                cleanup={
                    "server_stopped": result.server_stopped,
                    "request_gate_drained": result.request_gate_drained,
                    "server_closed": result.server_closed,
                    "session_removed": result.session_removed,
                },
                error_stage=result.error_stage,
            )
        self._page.deleteLater()
        self._profile.deleteLater()
        self._window.deleteLater()
        self._application.exit(exit_code)


def run_qt_shell() -> int:
    probe = activate_bundle_probe()
    application = QApplication.instance() or QApplication([])
    application.setQuitOnLastWindowClosed(False)
    token = secrets.token_urlsafe(32)
    session = GuiSession(temp_root=probe.session_root if probe else None)
    gate = RequestGate()
    window = ShellWindow()
    dialog = probe.dialog() if probe else QtSaveFileDialog(window)
    session.file_dialog = dialog
    flask_app = create_app(session_token=token, gui_session=session, request_gate=gate)
    server = start_loopback_server(flask_app)
    origin = server.url.rstrip("/")

    profile = QWebEngineProfile(window)
    interceptor = OriginInterceptor(origin, profile)
    profile.setUrlRequestInterceptor(interceptor)
    page = RestrictedPage(profile, origin, window)
    view = QWebEngineView(window)
    view.setPage(page)
    window.setCentralWidget(view)
    window.resize(1280, 720)
    window.setMinimumSize(640, 360)
    window.setWindowTitle("Summer GDS")
    coordinator = ShutdownCoordinator(
        application=application,
        window=window,
        page=page,
        profile=profile,
        dialog=dialog,
        server=server,
        gate=gate,
        session=session,
        probe=probe,
    )
    window.close_requested.connect(coordinator.begin)
    application.aboutToQuit.connect(coordinator.begin)

    probe_timer: QTimer | None = None
    probe_deadline: QTimer | None = None
    if probe is not None:
        probe_timer = QTimer(window)
        probe_timer.setInterval(100)

        def poll_probe_command() -> None:
            try:
                command = probe.read_command()
            except ProbeActivationError:
                coordinator.begin("invalid_probe_command")
                return
            if command == "shutdown":
                if probe_deadline is not None:
                    probe_deadline.stop()
                coordinator.begin()

        probe_timer.timeout.connect(poll_probe_command)
        probe_timer.start()
        probe_deadline = QTimer(window)
        probe_deadline.setSingleShot(True)
        probe_deadline.timeout.connect(lambda: coordinator.begin("probe_command_timeout"))
        probe_deadline.start(PROBE_TOTAL_TIMEOUT_SECONDS * 1000)

    def fatal(message: str) -> None:
        logging.critical(message)
        QMessageBox.critical(window, "Summer GDS", message)
        coordinator.begin()

    dom_deadline = 0.0

    def dom_checked(ready: object) -> None:
        if ready is not True:
            if time.monotonic() < dom_deadline:
                QTimer.singleShot(50, check_dom_ready)
                return
            fatal("The Summer GDS page did not initialize correctly.")
            return
        window.show()
        if probe is not None:
            probe.publish_ready(
                pid=os.getpid(),
                origin=origin,
                process_arch=platform.machine(),
            )

    def check_dom_ready() -> None:
        page.runJavaScript(DOM_READY_SCRIPT, dom_checked)

    def loaded(ok: bool) -> None:
        nonlocal dom_deadline
        if not ok:
            fatal("The Summer GDS page failed to load.")
            return
        dom_deadline = time.monotonic() + 5.0
        check_dom_ready()

    page.loadFinished.connect(loaded)
    page.renderProcessTerminated.connect(
        lambda _status, _code: coordinator.begin() if coordinator._state != "running" else fatal(
            "The Summer GDS renderer stopped unexpectedly."
        )
    )
    view.setUrl(QUrl(server.url))
    return application.exec()


def _origin(url: QUrl) -> str:
    parsed = urlsplit(url.toString())
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.port is None:
        return ""
    return f"http://127.0.0.1:{parsed.port}"
