from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

from summer_gds.gui.desktop import PyWebviewSaveFileDialog
from summer_gds.gui.launcher import start_loopback_server
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
