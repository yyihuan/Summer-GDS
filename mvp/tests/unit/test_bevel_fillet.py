from pathlib import Path

from mvp_summer_gds.config.loader import load_yaml_file
from mvp_summer_gds.config.schema import normalize_config
from mvp_summer_gds.geometry.fillet import apply_bevel
from mvp_summer_gds.geometry.primitives import signed_area
from mvp_summer_gds.geometry.renderer import render_config
from mvp_summer_gds.model import Point

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_apply_bevel_to_square_outputs_deterministic_points():
    points = [
        Point(0, 0),
        Point(100, 0),
        Point(100, 80),
        Point(0, 80),
    ]
    result = apply_bevel(points, [5, 5, 5, 5])
    assert [point.as_tuple() for point in result] == [
        (0.0, 5.0),
        (5.0, 0.0),
        (95.0, 0.0),
        (100.0, 5.0),
        (100.0, 75.0),
        (95.0, 80.0),
        (5.0, 80.0),
        (0.0, 75.0),
    ]
    assert signed_area(result) > 0


def test_zero_bevel_distance_preserves_corner():
    points = [
        Point(0, 0),
        Point(10, 0),
        Point(10, 10),
        Point(0, 10),
    ]
    result = apply_bevel(points, [0, 1, 0, 1])
    assert result[0].as_tuple() == (0, 0)
    assert result[3].as_tuple() == (10, 10)


def test_bevel_fixture_renders_eight_points():
    config = normalize_config(load_yaml_file(FIXTURES / "valid_polygon_bevel.yaml"))
    rendered = render_config(config)
    assert len(rendered[0].points) == 8
