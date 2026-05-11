from pathlib import Path

import pytest

from summer_gds.config.errors import ConfigValidationError
from summer_gds.config.loader import load_yaml_file
from summer_gds.config.schema import normalize_config
from summer_gds.model import CircleShape, PolygonShape

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "mvp"


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


def test_valid_bevel_normalizes_fillet():
    config = load_fixture("valid_polygon_bevel.yaml")
    assert config.shapes[0].fillet.mode == "bevel"
    assert config.shapes[0].fillet.distances == [5.0, 5.0, 5.0, 5.0]


def test_shape_layer_defaults_to_gds_default_layer():
    raw = load_yaml_file(FIXTURES / "valid_polygon.yaml")
    raw["gds"]["default_layer"] = [7, 3]
    raw["shapes"][0].pop("layer")
    config = normalize_config(raw)
    assert config.shapes[0].layer.as_tuple() == (7, 3)


def test_old_schema_is_rejected_with_specific_code():
    assert_error_code("invalid_old_polygon.yaml", "old_schema_detected")


def test_arc_fillet_is_rejected():
    assert_error_code("invalid_arc_fillet.yaml", "unsupported_fillet_mode")


def test_self_intersecting_polygon_is_rejected():
    assert_error_code("invalid_self_intersection.yaml", "self_intersecting_polygon")


def test_bevel_too_large_is_rejected():
    assert_error_code("invalid_bevel_too_large.yaml", "bevel_distance_too_large")


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
    raw["shapes"][0]["fillet"] = {"mode": "bevel", "distances": [1, 1, 1]}
    with pytest.raises(ConfigValidationError) as exc_info:
        normalize_config(raw)
    assert "circle_fillet_not_supported" in {issue.code for issue in exc_info.value.issues}


def test_precision_must_be_integer_multiple_of_dbu():
    raw = load_yaml_file(FIXTURES / "valid_polygon.yaml")
    raw["global"]["dbu"] = 0.003
    raw["global"]["precision"] = 0.01
    with pytest.raises(ConfigValidationError) as exc_info:
        normalize_config(raw)
    assert "precision_dbu_mismatch" in {issue.code for issue in exc_info.value.issues}
