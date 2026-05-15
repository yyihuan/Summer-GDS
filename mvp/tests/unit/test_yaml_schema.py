from pathlib import Path

import pytest

from mvp_summer_gds.config.errors import ConfigValidationError
from mvp_summer_gds.config.loader import load_yaml_file
from mvp_summer_gds.config.schema import normalize_config
from mvp_summer_gds.model import ArcFillet, CircleShape, PolygonShape

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load_fixture(name):
    return normalize_config(load_yaml_file(FIXTURES / name))


def assert_error_code(name, expected_code):
    with pytest.raises(ConfigValidationError) as exc_info:
        load_fixture(name)
    codes = {issue.code for issue in exc_info.value.issues}
    assert expected_code in codes


def test_valid_polygon_normalizes_to_model():
    config = load_fixture("valid_polygon.yaml")
    assert config.schema_version == 1
    assert config.gds.cell_name == "TOP"
    assert len(config.shapes) == 1
    assert isinstance(config.shapes[0], PolygonShape)
    assert config.shapes[0].layer.as_tuple() == (2, 0)


def test_valid_circle_normalizes_to_model():
    config = load_fixture("valid_circle.yaml")
    assert isinstance(config.shapes[0], CircleShape)
    assert config.shapes[0].center.as_tuple() == (50.0, 50.0)
    assert config.shapes[0].radius == 30.0


def test_valid_arc_normalizes_fillet_without_mode():
    config = load_fixture("valid_polygon_arc.yaml")
    assert isinstance(config.shapes[0].fillet, ArcFillet)
    assert config.shapes[0].fillet.mode == "arc"
    assert config.shapes[0].fillet.radii == [5.0, 5.0, 5.0, 5.0]
    assert config.shapes[0].fillet.precision is None


def test_valid_arc_normalizes_optional_mode():
    config = load_fixture("valid_polygon_arc_mode.yaml")
    assert isinstance(config.shapes[0].fillet, ArcFillet)
    assert config.shapes[0].fillet.mode == "arc"
    assert config.shapes[0].fillet.radii == [5.0, 5.0, 5.0, 5.0]


def test_valid_arc_precision_normalizes():
    config = load_fixture("valid_polygon_arc_precision.yaml")
    assert config.shapes[0].fillet.precision == 0.1


def test_valid_concave_arc_fixtures_normalize():
    arrow = load_fixture("valid_polygon_arc_arrow_concave.yaml")
    star = load_fixture("valid_polygon_arc_star_concave.yaml")

    assert isinstance(arrow.shapes[0].fillet, ArcFillet)
    assert isinstance(star.shapes[0].fillet, ArcFillet)


def test_shape_layer_defaults_to_gds_default_layer():
    raw = load_yaml_file(FIXTURES / "valid_polygon.yaml")
    raw["gds"]["default_layer"] = [7, 3]
    raw["shapes"][0].pop("layer")
    config = normalize_config(raw)
    assert config.shapes[0].layer.as_tuple() == (7, 3)


def test_old_schema_is_rejected_with_specific_code():
    assert_error_code("invalid_old_polygon.yaml", "old_schema_detected")


def test_unsupported_fillet_mode_is_rejected():
    assert_error_code("invalid_unsupported_fillet_mode.yaml", "unsupported_fillet_mode")


def test_unsupported_fillet_payload_is_rejected():
    raw = load_yaml_file(FIXTURES / "valid_polygon.yaml")
    raw["shapes"][0]["fillet"] = {"mode": "legacy", "distances": [1, 1, 1, 1]}
    with pytest.raises(ConfigValidationError) as exc_info:
        normalize_config(raw)
    assert "unsupported_fillet_mode" in {issue.code for issue in exc_info.value.issues}


def test_self_intersecting_polygon_is_rejected():
    assert_error_code("invalid_self_intersection.yaml", "self_intersecting_polygon")


def test_arc_too_large_is_rejected():
    assert_error_code("invalid_arc_too_large.yaml", "arc_radius_too_large")


def test_arc_too_large_sharp_corner_is_rejected():
    assert_error_code("invalid_arc_too_large_sharp.yaml", "arc_radius_too_large")


def test_arc_collinear_positive_radius_is_rejected():
    assert_error_code("invalid_arc_collinear_positive.yaml", "arc_collinear_corner")


def test_arc_length_mismatch_fixture_is_rejected():
    assert_error_code("invalid_arc_length_mismatch.yaml", "arc_radii_length_mismatch")


def test_arc_precision_fixture_is_rejected():
    assert_error_code("invalid_arc_precision.yaml", "arc_precision_out_of_range")


def test_circle_fillet_fixture_is_rejected():
    assert_error_code("invalid_circle_fillet.yaml", "circle_fillet_not_supported")


def test_valid_arc_sharp_convex_fixture_normalizes():
    config = load_fixture("valid_polygon_arc_sharp_convex.yaml")
    assert isinstance(config.shapes[0].fillet, ArcFillet)
    assert config.shapes[0].fillet.radii == [0.001, 0.001, 0.001]


def test_schema_version_must_be_integer_one():
    raw = load_yaml_file(FIXTURES / "valid_polygon.yaml")
    raw["schema_version"] = 1.0
    with pytest.raises(ConfigValidationError) as exc_info:
        normalize_config(raw)
    assert {issue.code for issue in exc_info.value.issues} == {"unsupported_schema_version"}


def test_unknown_top_level_field_is_rejected():
    raw = load_yaml_file(FIXTURES / "valid_polygon.yaml")
    raw["extra"] = True
    with pytest.raises(ConfigValidationError) as exc_info:
        normalize_config(raw)
    assert "unknown_field" in {issue.code for issue in exc_info.value.issues}


def test_string_vertices_are_rejected():
    raw = load_yaml_file(FIXTURES / "valid_polygon.yaml")
    raw["shapes"][0]["vertices"] = "0,0;100,0;100,80;0,80"
    with pytest.raises(ConfigValidationError) as exc_info:
        normalize_config(raw)
    assert "string_vertices_not_supported" in {issue.code for issue in exc_info.value.issues}


def test_circle_fillet_is_rejected():
    raw = load_yaml_file(FIXTURES / "valid_circle.yaml")
    raw["shapes"][0]["fillet"] = {"radii": [1, 1, 1]}
    with pytest.raises(ConfigValidationError) as exc_info:
        normalize_config(raw)
    assert "circle_fillet_not_supported" in {issue.code for issue in exc_info.value.issues}


def test_bare_radii_are_valid_arc_schema():
    raw = load_yaml_file(FIXTURES / "valid_polygon.yaml")
    raw["shapes"][0]["fillet"] = {"radii": [1, 1, 1, 1]}
    config = normalize_config(raw)
    assert isinstance(config.shapes[0].fillet, ArcFillet)


def test_precision_must_be_integer_multiple_of_dbu():
    raw = load_yaml_file(FIXTURES / "valid_polygon.yaml")
    raw["global"]["dbu"] = 0.003
    raw["global"]["precision"] = 0.01
    with pytest.raises(ConfigValidationError) as exc_info:
        normalize_config(raw)
    assert "precision_dbu_mismatch" in {issue.code for issue in exc_info.value.issues}
