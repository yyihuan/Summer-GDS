from __future__ import annotations

from pathlib import Path

from summer_gds.gui.server import create_app


TOKEN = "test-token"


def test_index_is_local_static_shell(tmp_path):
    app = create_app(session_token=TOKEN, temp_root=tmp_path)
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Summer GDS" in html
    assert TOKEN in html
    assert "http://" not in html
    assert "https://" not in html
    assert "cdn" not in html.lower()
    assert "/static/style.css" in html
    assert "/static/app.js" in html


def test_index_is_builder_first_not_yaml_editor(tmp_path):
    app = create_app(session_token=TOKEN, temp_root=tmp_path)
    client = app.test_client()

    response = client.get("/")

    html = response.get_data(as_text=True)
    assert "构建器" in html
    assert "YAML 预览" in html
    assert "全局设置" in html
    assert "+ 基础图形" in html
    assert "+ Via" in html
    assert "+ Rings" in html
    assert "shapeList" in html
    assert "yamlPreview" in html
    assert "vertexListInput" in html
    assert "vertexLineNumbers" in html
    assert "formatVertexListButton" in html
    assert "baseFilletModeInput" in html
    assert "baseFilletRadiiInput" in html
    assert "formatBaseFilletRadiiButton" in html
    assert "viaInnerFilletModeInput" in html
    assert "viaInnerFilletRadiiInput" in html
    assert "viaOuterFilletModeInput" in html
    assert "viaOuterConcentricInput" in html
    assert "viaOuterFilletRadiiInput" in html
    assert "ringsConcentricFilletModeInput" in html
    assert "ringsConcentricRadiiInput" in html
    assert "vertexTable" not in html
    assert "+ 点" not in html
    assert "id=\"yamlEditor\"" not in html
    assert "Preview SVG" not in html


def test_frontend_guards_against_stuck_busy_state():
    script = (Path(__file__).parents[2] / "src/summer_gds/gui/static/app.js").read_text()

    assert "REQUEST_TIMEOUT_MS" in script
    assert "FILE_DIALOG_TIMEOUT_MS" in script
    assert "busyWatchdogTimer" in script
    assert "function guardBusy()" in script
    assert "TimeoutError" in script


def test_frontend_uses_single_vertex_list_input_with_orientation_checks():
    script = (Path(__file__).parents[2] / "src/summer_gds/gui/static/app.js").read_text()

    assert "function parseVertexList" in script
    assert "function parseDelimitedVertices" in script
    assert "function parseYamlStyleVertices" in script
    assert "function polygonSignedArea" in script
    assert "当前点序为顺时针" in script
    assert "首尾点重复" in script
    assert "TODO: 后续加入更智能的格式识别" in script


def test_frontend_supports_base_shape_per_corner_fillet_radii():
    script = (Path(__file__).parents[2] / "src/summer_gds/gui/static/app.js").read_text()

    assert "function parseRadiiList" in script
    assert "function parseDelimitedRadii" in script
    assert "function formatRadiiForList" in script
    assert "function baseFilletRadiiExpectedCount" in script
    assert "半径数量为" in script
    assert "offset 后由预览校验" in script
    assert "radii:" in script


def test_frontend_supports_via_inner_outer_per_corner_fillet_radii():
    script = (Path(__file__).parents[2] / "src/summer_gds/gui/static/app.js").read_text()

    assert "function readViaFilletSide" in script
    assert "function formatViaFilletRadiiList" in script
    assert "viaInnerFilletRadiiInput" in script
    assert "viaOuterFilletRadiiInput" in script
    assert "function computeViaOuterConcentricSpec" in script
    assert "function markViaOuterOverride" in script
    assert "formatRadiusSpecInline" in script


def test_frontend_supports_rings_concentric_fillet_expansion():
    script = (Path(__file__).parents[2] / "src/summer_gds/gui/static/app.js").read_text()

    assert "function readRingsConcentricFillet" in script
    assert "function addRadiusOffset" in script
    assert "function formatRingsConcentricRadiiList" in script
    assert "ringsConcentricFilletModeInput" in script
