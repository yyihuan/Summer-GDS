from __future__ import annotations

import sys
from pathlib import Path
from urllib.request import urlopen

from summer_gds.gui.desktop import PyWebviewSaveFileDialog
from summer_gds.gui.launcher import launch_desktop, start_loopback_server
from summer_gds.gui.server import create_app


def test_loopback_server_serves_gui_and_stops(tmp_path):
    app = create_app(session_token="test-token", temp_root=tmp_path)
    handle = start_loopback_server(app)
    try:
        with urlopen(handle.url, timeout=2) as response:
            html = response.read().decode("utf-8")
    finally:
        handle.stop()

    assert handle.host == "127.0.0.1"
    assert handle.port > 0
    assert "Summer GDS" in html
    assert "test-token" in html


class FakeWebviewModule:
    guilib = None
    renderer = None

    def __init__(self):
        self.created_windows = []
        self.start_kwargs = None
        self.initialize_called = False

    def initialize(self):
        self.initialize_called = True
        raise AssertionError("launch_desktop must not pre-initialize pywebview")

    def create_window(self, *args, **kwargs):
        self.created_windows.append((args, kwargs))
        return FakeWindow(None)

    def start(self, **kwargs):
        self.start_kwargs = kwargs
        self.guilib = "fake-guilib"
        self.renderer = kwargs.get("gui") or "default"
        callback = kwargs.get("func")
        callback_args = kwargs.get("args") or ()
        if callback is not None:
            callback(*callback_args)


class FakeServerHandle:
    url = "http://127.0.0.1:12345/"

    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


def test_launch_desktop_forces_edgechromium_on_windows(monkeypatch, tmp_path):
    fake_webview = FakeWebviewModule()
    fake_handle = FakeServerHandle()
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("summer_gds.gui.launcher.start_loopback_server", lambda _app: fake_handle)

    launch_desktop(
        session_token="test-token",
        temp_root=tmp_path,
        webview_module=fake_webview,
    )

    assert fake_webview.initialize_called is False
    assert fake_webview.start_kwargs["gui"] == "edgechromium"
    assert callable(fake_webview.start_kwargs["func"])
    assert fake_handle.stopped is True


class FakeWindow:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def create_file_dialog(self, dialog_type, **kwargs):
        self.calls.append((dialog_type, kwargs))
        return self.result


def test_pywebview_save_dialog_returns_selected_path(tmp_path):
    selected = tmp_path / "layout.gds"
    window = FakeWindow([str(selected)])
    dialog = PyWebviewSaveFileDialog(window=window, save_dialog_constant="SAVE")

    result = dialog.choose_save_path("gds", "layout.gds")

    assert result == selected
    assert window.calls == [
        (
            "SAVE",
            {
                "save_filename": "layout.gds",
                "file_types": ("GDSII layout (*.gds)",),
            },
        )
    ]


def test_pywebview_save_dialog_maps_yaml_and_cancel():
    window = FakeWindow(None)
    dialog = PyWebviewSaveFileDialog(window=window, save_dialog_constant="SAVE")

    result = dialog.choose_save_path("yaml", "config.yaml")

    assert result is None
    assert window.calls[0][1]["file_types"] == ("YAML config (*.yaml;*.yml)",)


def test_pywebview_open_dialog_maps_yaml(tmp_path):
    selected = tmp_path / "config.yaml"
    window = FakeWindow((str(selected),))
    dialog = PyWebviewSaveFileDialog(window=window, open_dialog_constant="OPEN")

    result = dialog.choose_open_path("yaml")

    assert result == selected
    assert window.calls == [
        (
            "OPEN",
            {
                "file_types": ("YAML config (*.yaml;*.yml)",),
            },
        )
    ]
