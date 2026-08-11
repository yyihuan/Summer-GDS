from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QFileDialog, QWidget

from summer_gds.gui.service import DialogFailure


DIALOG_WAIT_TIMEOUT_SECONDS = 100.0
TerminalState = Literal["selected", "canceled", "failed", "timed_out", "closing"]


@dataclass
class _DialogRequest:
    kind: str
    suggested_name: str | None
    mode: Literal["open", "save"]
    event: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)
    state: TerminalState | None = None
    path: Path | None = None
    error: DialogFailure | None = None
    dialog: QFileDialog | None = None

    def complete(
        self,
        state: TerminalState,
        *,
        path: Path | None = None,
        error: DialogFailure | None = None,
    ) -> bool:
        with self.lock:
            if self.state is not None:
                return False
            self.state = state
            self.path = path
            self.error = error
            self.event.set()
            return True


class QtSaveFileDialog(QObject):
    """Synchronous worker-facing adapter backed by GUI-thread asynchronous dialogs."""

    request_dialog = Signal(object)
    cancel_dialog = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        timeout: float = DIALOG_WAIT_TIMEOUT_SECONDS,
        dialog_factory: Callable[[QWidget | None], QFileDialog] = QFileDialog,
    ) -> None:
        super().__init__(parent)
        self._parent = parent
        self._timeout = timeout
        self._dialog_factory = dialog_factory
        self._state_lock = threading.Lock()
        self._active: _DialogRequest | None = None
        self._closing = False
        self.request_dialog.connect(self._show_dialog)
        self.cancel_dialog.connect(self._cancel_on_gui_thread)

    def choose_open_path(self, kind: str) -> Path | None:
        return self._choose("open", kind, None)

    def choose_save_path(self, kind: str, suggested_name: str | None) -> Path | None:
        return self._choose("save", kind, suggested_name)

    def _choose(self, mode: Literal["open", "save"], kind: str, suggested_name: str | None) -> Path | None:
        request = _DialogRequest(kind=kind, suggested_name=suggested_name, mode=mode)
        with self._state_lock:
            if self._closing:
                return None
            if self._active is not None:
                raise DialogFailure("dialog_busy", "Another file dialog is already open.")
            self._active = request
        self.request_dialog.emit(request)
        if not request.event.wait(self._timeout):
            timed_out = request.complete(
                "timed_out",
                error=DialogFailure("dialog_timeout", "The file dialog timed out."),
            )
            if timed_out:
                self.cancel_dialog.emit(request)
        with request.lock:
            state, path, error = request.state, request.path, request.error
        if error is not None:
            raise error
        if state == "selected":
            return path
        return None

    def begin_shutdown(self) -> None:
        with self._state_lock:
            self._closing = True
            active = self._active
        if active is not None:
            active.complete("closing")
            self.cancel_dialog.emit(active)

    @Slot(object)
    def _show_dialog(self, request: _DialogRequest) -> None:
        with request.lock:
            already_terminal = request.state is not None
        if already_terminal:
            self._release_if_closed(request)
            return
        try:
            dialog = self._dialog_factory(self._parent)
            request.dialog = dialog
            dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
            dialog.setAcceptMode(
                QFileDialog.AcceptMode.AcceptOpen
                if request.mode == "open"
                else QFileDialog.AcceptMode.AcceptSave
            )
            dialog.setNameFilter(_name_filter(request.kind))
            if request.mode == "save" and request.suggested_name:
                dialog.selectFile(request.suggested_name)
            dialog.finished.connect(lambda result: self._dialog_finished(request, result))
            dialog.open()
        except Exception:
            request.complete(
                "failed",
                error=DialogFailure("dialog_error", "The file dialog could not be opened."),
            )
            self._release(request)

    @Slot(object)
    def _cancel_on_gui_thread(self, request: _DialogRequest) -> None:
        dialog = request.dialog
        if dialog is None:
            self._release(request)
            return
        dialog.reject()

    def _dialog_finished(self, request: _DialogRequest, result: int) -> None:
        try:
            selected = request.dialog.selectedFiles() if request.dialog is not None else []
            if result == QFileDialog.DialogCode.Accepted and selected:
                request.complete("selected", path=Path(selected[0]))
            else:
                request.complete("canceled")
        except Exception:
            request.complete(
                "failed",
                error=DialogFailure("dialog_error", "The file dialog failed."),
            )
        finally:
            if request.dialog is not None:
                request.dialog.deleteLater()
            self._release(request)

    def _release_if_closed(self, request: _DialogRequest) -> None:
        with request.lock:
            terminal = request.state
        if terminal in {"timed_out", "closing"}:
            self._release(request)

    def _release(self, request: _DialogRequest) -> None:
        with self._state_lock:
            if self._active is request:
                self._active = None


def _name_filter(kind: str) -> str:
    if kind == "gds":
        return "GDSII layout (*.gds)"
    if kind == "yaml":
        return "YAML config (*.yaml *.yml)"
    return "All files (*)"
