from __future__ import annotations

from pathlib import Path

from summer_gds.gui.server import create_app


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


def make_client(tmp_path: Path):
    app = create_app(session_token=TOKEN, temp_root=tmp_path)
    return app.test_client()


def post_json(client, path: str, payload: dict, token: str | None = TOKEN):
    headers = {"X-Summer-GDS-Token": token} if token is not None else {}
    return client.post(path, json=payload, headers=headers)


def test_api_rejects_missing_session_token(tmp_path):
    client = make_client(tmp_path)

    response = post_json(client, "/api/parse", {"yaml_text": VALID_YAML}, token=None)

    assert response.status_code == 403
    data = response.get_json()
    assert data["ok"] is False
    assert data["errors"][0]["code"] == "forbidden"


def test_parse_returns_normalized_config_and_field_map(tmp_path):
    client = make_client(tmp_path)

    response = post_json(client, "/api/parse", {"yaml_text": VALID_YAML})

    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["parsed_config"]["schema_version"] == 2
    assert data["parsed_config"]["global"]["dbu"] == 0.001
    assert data["parsed_config"]["shapes"][0]["type"] == "base_shape"
    assert data["parsed_config"]["shapes"][0]["layer"] == [1, 0]
    assert data["canonical_yaml"].startswith("schema_version: 2")
    assert data["field_map"]["$.global.dbu"] == "global.dbu"
    assert data["errors"] == []


def test_parse_reports_contract_errors_without_throwing(tmp_path):
    client = make_client(tmp_path)
    yaml_text = VALID_YAML.replace("sid: 0", "sid: true")

    response = post_json(client, "/api/parse", {"yaml_text": yaml_text})

    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is False
    assert data["parsed_config"] is None
    assert {error["code"] for error in data["errors"]} == {"invalid_type"}


def test_validate_checks_yaml_contract_without_preview_generation(tmp_path):
    client = make_client(tmp_path)

    response = post_json(client, "/api/validate", {"yaml_text": VALID_YAML})

    assert response.status_code == 200
    data = response.get_json()
    assert data == {"ok": True, "shape_count": 1, "errors": []}
    assert not list(tmp_path.rglob("*.svg"))


def test_preview_svg_returns_svg_text_and_removes_temp_files(tmp_path):
    client = make_client(tmp_path)

    response = post_json(client, "/api/preview/svg", {"yaml_text": VALID_YAML, "request_id": "r1"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["region_count"] == 1
    assert data["svg_text"].lstrip().startswith("<?xml")
    assert "<svg" in data["svg_text"]
    assert data["errors"] == []
    assert not list(tmp_path.rglob("*.svg"))
    assert not list(tmp_path.rglob("*.yaml"))


def test_preview_svg_reports_geometry_errors(tmp_path):
    client = make_client(tmp_path)
    yaml_text = VALID_YAML.replace(
        "[[0, 0], [100, 0], [100, 80], [0, 80]]",
        "[[0, 0], [100, 100], [0, 100], [100, 0]]",
    )

    response = post_json(client, "/api/preview/svg", {"yaml_text": yaml_text, "request_id": "bad"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is False
    assert data["svg_text"] is None
    assert {error["code"] for error in data["errors"]} == {"invalid_boundary"}
