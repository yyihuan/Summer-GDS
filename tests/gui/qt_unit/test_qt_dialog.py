from __future__ import annotations

import threading
import time

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QFileDialog

from summer_gds.gui.qt_dialog import QtSaveFileDialog
from summer_gds.gui.service import DialogFailure


class FakeDialog(QObject):
    finished = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.paths: list[str] = []
        self.opened = False
        self.rejected = False

    def setFileMode(self, _mode):
        pass

    def setAcceptMode(self, _mode):
        pass

    def setNameFilter(self, _filter):
        pass

    def selectFile(self, path):
        self.paths = [path]

    def selectedFiles(self):
        return self.paths

    def open(self):
        self.opened = True

    def reject(self):
        self.rejected = True
        self.finished.emit(QFileDialog.DialogCode.Rejected)


@pytest.fixture
def application():
    return QApplication.instance() or QApplication([])


def _pump_until(application, predicate, timeout=1.0):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.001)
    assert predicate()


def test_second_dialog_returns_busy_without_queueing(application):
    created: list[FakeDialog] = []
    bridge = QtSaveFileDialog(
        timeout=1,
        dialog_factory=lambda parent: created.append(FakeDialog(parent)) or created[-1],
    )
    result: list[object] = []
    worker = threading.Thread(target=lambda: result.append(bridge.choose_open_path("yaml")))
    worker.start()
    _pump_until(application, lambda: bool(created and created[0].opened))

    with pytest.raises(DialogFailure) as exc:
        bridge.choose_save_path("yaml", "配置 🧪.yaml")
    assert exc.value.code == "dialog_busy"
    assert len(created) == 1

    created[0].finished.emit(QFileDialog.DialogCode.Rejected)
    worker.join(1)
    assert result == [None]


def test_selected_unicode_path_is_returned(application, tmp_path):
    selected = tmp_path / "中文 emoji 🧪 config.yaml"
    created: list[FakeDialog] = []
    bridge = QtSaveFileDialog(
        timeout=1,
        dialog_factory=lambda parent: created.append(FakeDialog(parent)) or created[-1],
    )
    result: list[object] = []
    worker = threading.Thread(target=lambda: result.append(bridge.choose_save_path("yaml", selected.name)))
    worker.start()
    _pump_until(application, lambda: bool(created and created[0].opened))
    created[0].paths = [str(selected)]
    created[0].finished.emit(QFileDialog.DialogCode.Accepted)
    worker.join(1)
    assert result == [selected]


def test_timeout_discards_late_selection_and_keeps_single_flight(application, tmp_path):
    created: list[FakeDialog] = []
    bridge = QtSaveFileDialog(
        timeout=0.02,
        dialog_factory=lambda parent: created.append(FakeDialog(parent)) or created[-1],
    )
    errors: list[str] = []

    def choose():
        try:
            bridge.choose_open_path("yaml")
        except DialogFailure as exc:
            errors.append(exc.code)

    worker = threading.Thread(target=choose)
    worker.start()
    _pump_until(application, lambda: bool(created and created[0].opened))
    worker.join(1)
    assert errors == ["dialog_timeout"]
    with pytest.raises(DialogFailure) as exc:
        bridge.choose_open_path("yaml")
    assert exc.value.code == "dialog_busy"

    created[0].paths = [str(tmp_path / "late.yaml")]
    application.processEvents()
    assert created[0].rejected is True


def test_shutdown_wakes_pending_dialog(application):
    created: list[FakeDialog] = []
    bridge = QtSaveFileDialog(
        timeout=1,
        dialog_factory=lambda parent: created.append(FakeDialog(parent)) or created[-1],
    )
    result: list[object] = []
    worker = threading.Thread(target=lambda: result.append(bridge.choose_open_path("yaml")))
    worker.start()
    _pump_until(application, lambda: bool(created and created[0].opened))
    bridge.begin_shutdown()
    worker.join(1)
    application.processEvents()
    assert result == [None]
