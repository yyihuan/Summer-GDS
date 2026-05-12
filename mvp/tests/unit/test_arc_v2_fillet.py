from pathlib import Path

import pytest

from mvp_summer_gds.config.loader import load_yaml_file
from mvp_summer_gds.config.schema import normalize_config
from mvp_summer_gds.geometry.fillet import apply_arc_v2, build_arc_corner_plans, validate_arc_radii
from mvp_summer_gds.geometry.primitives import signed_area
from mvp_summer_gds.geometry.renderer import render_config
from mvp_summer_gds.model import Point

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_apply_arc_v2_to_square_builds_corner_plans():
    points = [
        Point(0, 0),
        Point(100, 0),
        Point(100, 80),
        Point(0, 80),
    ]
    plans = build_arc_corner_plans(points, [5, 5, 5, 5])

    assert len(plans) == 4
    assert plans[0].tangent_start.as_tuple() == pytest.approx((0.0, 5.0))
    assert plans[0].tangent_end.as_tuple() == pytest.approx((5.0, 0.0))
    assert plans[0].center.as_tuple() == pytest.approx((5.0, 5.0))
    assert plans[0].segment_count > 2


def test_apply_arc_v2_outputs_ccw_polygon_with_arc_points():
    points = [
        Point(0, 0),
        Point(100, 0),
        Point(100, 80),
        Point(0, 80),
    ]
    result = apply_arc_v2(points, [5, 5, 5, 5])

    assert len(result) > 8
    assert result[0].as_tuple() == pytest.approx((0.0, 5.0))
    assert result[-1].as_tuple() == pytest.approx((0.0, 75.0))
    assert signed_area(result) > 0


def test_mixed_arc_v2_zero_radius_preserves_corner():
    points = [
        Point(0, 0),
        Point(100, 0),
        Point(100, 80),
        Point(0, 80),
    ]
    plans = build_arc_corner_plans(points, [0, 4, 8, 2])

    assert plans[0].output_points == [Point(0, 0)]
    assert plans[1].center.as_tuple() == pytest.approx((96.0, 4.0))
    assert plans[2].center.as_tuple() == pytest.approx((92.0, 72.0))
    assert plans[3].center.as_tuple() == pytest.approx((2.0, 78.0))


def test_arc_v2_fixture_renders_many_points():
    config = normalize_config(load_yaml_file(FIXTURES / "valid_polygon_arc_v2.yaml"))
    rendered = render_config(config)

    assert len(rendered) == 1
    assert len(rendered[0].points) > 8
    assert signed_area(rendered[0].points) > 0


def test_arc_v2_clockwise_input_preserves_user_radius_mapping(tmp_path):
    config_path = tmp_path / "clockwise_arc.yaml"
    config_path.write_text(
        """
schema_version: 1
global:
  dbu: 0.001
  precision: null
gds:
  output_file: "clockwise_arc.gds"
  cell_name: "TOP"
  default_layer: [1, 0]
shapes:
  - id: "cw_arc"
    type: "base_shape"
    geometry_type: "polygon"
    name: "clockwise arc"
    layer: [2, 0]
    vertices:
      - [0, 0]
      - [0, 10]
      - [10, 10]
      - [10, 0]
    fillet:
      mode: "arc_v2"
      radii: [1, 2, 3, 4]
""",
        encoding="utf-8",
    )
    config = normalize_config(load_yaml_file(config_path))
    shape = config.shapes[0]

    assert shape.vertex_user_indices == [3, 2, 1, 0]
    assert shape.fillet.radii == [4.0, 3.0, 2.0, 1.0]


def test_validate_arc_v2_rejects_negative_radius():
    issues = validate_arc_radii(
        [Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)],
        [1, -1, 1, 1],
        "fillet.radii",
    )
    assert {issue.code for issue in issues} == {"negative_arc_radius"}


def test_validate_arc_v2_reports_user_index_after_normalization():
    issues = validate_arc_radii(
        [Point(10, 0), Point(10, 10), Point(0, 10), Point(0, 0)],
        [4, 3, 2, -1],
        "fillet.radii",
        [3, 2, 1, 0],
    )

    assert issues[0].path == "fillet.radii[0]"
