from pathlib import Path

from mvp_summer_gds.config.loader import load_yaml_file
from mvp_summer_gds.config.schema import normalize_config
from mvp_summer_gds.geometry.circle import DEFAULT_CIRCLE_SEGMENTS, approximate_circle
from mvp_summer_gds.geometry.primitives import signed_area
from mvp_summer_gds.geometry.renderer import render_config
from mvp_summer_gds.model import Point

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load_config(name):
    return normalize_config(load_yaml_file(FIXTURES / name))


def test_polygon_renders_without_fillet():
    rendered = render_config(load_config("valid_polygon.yaml"))
    assert len(rendered) == 1
    assert rendered[0].id == "main_pad"
    assert rendered[0].layer.as_tuple() == (2, 0)
    assert [point.as_tuple() for point in rendered[0].points] == [
        (0.0, 0.0),
        (100.0, 0.0),
        (100.0, 80.0),
        (0.0, 80.0),
    ]


def test_circle_renders_to_fixed_ccw_polygon():
    center = Point(50, 50)
    points = approximate_circle(center, 30)
    assert len(points) == DEFAULT_CIRCLE_SEGMENTS
    assert points[0].as_tuple() == (80.0, 50.0)
    assert signed_area(points) > 0


def test_circle_config_renders_one_polygon():
    rendered = render_config(load_config("valid_circle.yaml"))
    assert len(rendered) == 1
    assert len(rendered[0].points) == DEFAULT_CIRCLE_SEGMENTS
    assert rendered[0].layer.as_tuple() == (3, 0)
