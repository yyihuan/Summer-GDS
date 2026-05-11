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


def test_old_schema_is_rejected_with_specific_code():
    assert_error_code("invalid_old_polygon.yaml", "old_schema_detected")


def test_arc_fillet_is_rejected():
    assert_error_code("invalid_arc_fillet.yaml", "old_fillet_schema")


def test_self_intersecting_polygon_is_rejected():
    assert_error_code("invalid_self_intersection.yaml", "self_intersecting_polygon")


def test_bevel_too_large_is_rejected():
    assert_error_code("invalid_bevel_too_large.yaml", "bevel_distance_too_large")
