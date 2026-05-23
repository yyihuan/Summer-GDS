from __future__ import annotations

from collections import deque
from pathlib import Path

from summer_gds.gui.server import create_app
from summer_gds.gui.service import GuiSession


TOKEN = "test-token"

VALID_YAML = """
schema_version: 2
global:
  unit: um
  dbu: 0.001
gds:
  top_cell: TOP
shapes:
  - type: base_shape
    sid: 0
    name: source
    layer: [1, 0]
    source:
      vertices: [[0, 0], [100, 0], [100, 80], [0, 80]]
"""


class FakeSaveDialog:
    def __init__(self, *paths: Path | None):
        self.paths = deque(paths)
        self.calls: list[tuple[str, str | None]] = []

    def choose_save_path(self, kind: str, suggested_name: str | None) -> Path | None:
        self.calls.append((kind, suggested_name))
        return self.paths.popleft()


def make_client(tmp_path: Path, dialog: FakeSaveDialog):
    session = GuiSession(temp_root=tmp_path / "gui-temp", file_dialog=dialog)
    app = create_app(session_token=TOKEN, gui_session=session)
    return app.test_client()


def post_json(client, path: str, payload: dict):
    return client.post(path, json=payload, headers={"X-Summer-GDS-Token": TOKEN})


def choose_path(client, kind: str, suggested_name: str | None = None) -> dict:
    payload = {"kind": kind}
    if suggested_name is not None:
        payload["suggested_name"] = suggested_name
    response = post_json(client, "/api/file/choose-save", payload)
    assert response.status_code == 200
    return response.get_json()


def test_choose_save_returns_token_without_writing(tmp_path):
    output = tmp_path / "layout.gds"
    dialog = FakeSaveDialog(output)
    client = make_client(tmp_path, dialog)

    data = choose_path(client, "gds", suggested_name="layout.gds")

    assert data["ok"] is True
    assert data["path_token"]
    assert data["path_label"] == str(output)
    assert data["exists"] is False
    assert data["errors"] == []
    assert dialog.calls == [("gds", "layout.gds")]
    assert not output.exists()


def test_choose_save_cancel_is_explicit(tmp_path):
    client = make_client(tmp_path, FakeSaveDialog(None))

    data = choose_path(client, "yaml")

    assert data == {"ok": False, "canceled": True, "errors": []}


def test_yaml_save_validates_token_kind_and_writes_atomically(tmp_path):
    output = tmp_path / "config.yaml"
    client = make_client(tmp_path, FakeSaveDialog(output))
    token = choose_path(client, "yaml")["path_token"]

    response = post_json(client, "/api/yaml/save", {"yaml_text": VALID_YAML, "path_token": token})

    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["path_label"] == str(output)
    assert data["errors"] == []
    assert output.read_text() == VALID_YAML
    assert not (output.parent / ".config.tmp.yaml").exists()


def test_yaml_save_rejects_wrong_token_kind(tmp_path):
    client = make_client(tmp_path, FakeSaveDialog(tmp_path / "layout.gds"))
    token = choose_path(client, "gds")["path_token"]

    response = post_json(client, "/api/yaml/save", {"yaml_text": VALID_YAML, "path_token": token})

    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is False
    assert {error["code"] for error in data["errors"]} == {"invalid_path_token"}


def test_yaml_save_requires_force_for_existing_file(tmp_path):
    output = tmp_path / "config.yaml"
    output.write_text("old")
    client = make_client(tmp_path, FakeSaveDialog(output))
    token = choose_path(client, "yaml")["path_token"]

    blocked = post_json(client, "/api/yaml/save", {"yaml_text": VALID_YAML, "path_token": token})
    forced = post_json(client, "/api/yaml/save", {"yaml_text": VALID_YAML, "path_token": token, "force": True})

    assert blocked.get_json()["ok"] is False
    assert {error["code"] for error in blocked.get_json()["errors"]} == {"export_exists"}
    assert forced.get_json()["ok"] is True
    assert output.read_text() == VALID_YAML


def test_gds_export_uses_selected_token_path_not_gds_output(tmp_path):
    selected = tmp_path / "selected.gds"
    yaml_text = VALID_YAML.replace("top_cell: TOP", "top_cell: TOP\n  output: ignored.gds")
    client = make_client(tmp_path, FakeSaveDialog(selected))
    token = choose_path(client, "gds")["path_token"]

    response = post_json(client, "/api/export/gds", {"yaml_text": yaml_text, "path_token": token})

    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["path_label"] == str(selected)
    assert data["region_count"] == 1
    assert selected.exists()
    assert selected.stat().st_size > 0
    assert not (tmp_path / "ignored.gds").exists()


def test_gds_export_reports_missing_parent(tmp_path):
    missing_parent = tmp_path / "missing" / "layout.gds"
    client = make_client(tmp_path, FakeSaveDialog(missing_parent))
    token = choose_path(client, "gds")["path_token"]

    response = post_json(client, "/api/export/gds", {"yaml_text": VALID_YAML, "path_token": token})

    data = response.get_json()
    assert data["ok"] is False
    assert {error["code"] for error in data["errors"]} == {"path_missing"}
