from pathlib import Path

import pytest

from mvp_summer_gds.config.loader import load_yaml_file
from mvp_summer_gds.config.schema import normalize_config
from mvp_summer_gds.geometry.corners import CornerKind
from mvp_summer_gds.geometry.fillet import (
    MAX_ARC_SEGMENTS_PER_CORNER,
    apply_arc,
    build_arc_corner_plans,
    default_arc_precision,
    validate_arc_radii,
)
from mvp_summer_gds.geometry.primitives import distance, is_simple_polygon, signed_area
from mvp_summer_gds.geometry.renderer import render_config
from mvp_summer_gds.model import Point

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_apply_arc_to_square_builds_corner_plans():
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


def test_apply_arc_outputs_ccw_polygon_with_arc_points():
    points = [
        Point(0, 0),
        Point(100, 0),
        Point(100, 80),
        Point(0, 80),
    ]
    result = apply_arc(points, [5, 5, 5, 5])

    assert len(result) > 8
    assert result[0].as_tuple() == pytest.approx((0.0, 5.0))
    assert result[-1].as_tuple() == pytest.approx((0.0, 75.0))
    assert signed_area(result) > 0


def test_mixed_arc_zero_radius_preserves_corner():
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


def test_arc_fixture_renders_many_points():
    config = normalize_config(load_yaml_file(FIXTURES / "valid_polygon_arc.yaml"))
    rendered = render_config(config)

    assert len(rendered) == 1
    assert len(rendered[0].points) > 8
    assert signed_area(rendered[0].points) > 0


def test_arc_sharp_convex_fixture_renders_bounded_simple_polygon():
    config = normalize_config(load_yaml_file(FIXTURES / "valid_polygon_arc_sharp_convex.yaml"))
    rendered = render_config(config)
    points = rendered[0].points

    assert len(points) > 6
    assert len(points) < 20000
    assert signed_area(points) > 0
    assert is_simple_polygon(points)
    assert all(distance(points[index], points[(index + 1) % len(points)]) > 0 for index in range(len(points)))


def test_arc_sharp_convex_corner_plans_stay_under_segment_cap():
    points = [
        Point(0, 0),
        Point(100, 0),
        Point(1, 0.1),
    ]
    plans = build_arc_corner_plans(points, [0.001, 0.001, 0.001])

    assert len(plans) == 3
    assert all(2 <= plan.segment_count <= MAX_ARC_SEGMENTS_PER_CORNER for plan in plans)
    assert all(plan.center is not None for plan in plans)


def test_arc_clockwise_input_preserves_user_radius_mapping(tmp_path):
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
      radii: [1, 2, 3, 4]
""",
        encoding="utf-8",
    )
    config = normalize_config(load_yaml_file(config_path))
    shape = config.shapes[0]

    assert shape.vertex_user_indices == [3, 2, 1, 0]
    assert shape.fillet.radii == [4.0, 3.0, 2.0, 1.0]


def test_validate_arc_rejects_negative_radius():
    issues = validate_arc_radii(
        [Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)],
        [1, -1, 1, 1],
        "fillet.radii",
    )
    assert {issue.code for issue in issues} == {"negative_arc_radius"}


def test_arc_accepts_concave_arrow_with_minor_sweeps():
    config = normalize_config(load_yaml_file(FIXTURES / "valid_polygon_arc_arrow_concave.yaml"))
    shape = config.shapes[0]
    plans = build_arc_corner_plans(shape.vertices, shape.fillet.radii)
    rendered = render_config(config)
    points = rendered[0].points

    assert CornerKind.CONCAVE in {plan.context.corner_kind for plan in plans}
    assert {plan.sweep_direction for plan in plans if plan.segment_count > 0} == {-1, 1}
    assert signed_area(points) > 0
    assert is_simple_polygon(points)


def test_arc_accepts_concave_star_polygon():
    config = normalize_config(load_yaml_file(FIXTURES / "valid_polygon_arc_star_concave.yaml"))
    plans = build_arc_corner_plans(config.shapes[0].vertices, config.shapes[0].fillet.radii)
    rendered = render_config(config)
    points = rendered[0].points

    assert CornerKind.CONCAVE in {plan.context.corner_kind for plan in plans}
    assert signed_area(points) > 0
    assert is_simple_polygon(points)


def test_arc_octagon_fixtures_render_and_exercise_default_precision_switch():
    large_config = normalize_config(load_yaml_file(FIXTURES / "valid_polygon_arc_octagon_um.yaml"))
    small_config = normalize_config(load_yaml_file(FIXTURES / "valid_polygon_arc_octagon_scaled.yaml"))
    large_shape = large_config.shapes[0]
    small_shape = small_config.shapes[0]

    large_default = build_arc_corner_plans(large_shape.vertices, large_shape.fillet.radii)
    large_forced_fine = build_arc_corner_plans(large_shape.vertices, large_shape.fillet.radii, precision=0.001)
    small_default = build_arc_corner_plans(small_shape.vertices, small_shape.fillet.radii)
    small_forced_coarse = build_arc_corner_plans(small_shape.vertices, small_shape.fillet.radii, precision=0.01)

    assert large_shape.fillet.precision is None
    assert small_shape.fillet.precision is None
    assert default_arc_precision(500) == 0.01
    assert default_arc_precision(5) == 0.001
    assert max(plan.segment_count for plan in large_default) < max(plan.segment_count for plan in large_forced_fine)
    assert min(plan.segment_count for plan in small_default) > max(plan.segment_count for plan in small_forced_coarse)

    for config in (large_config, small_config):
        rendered = render_config(config)
        assert len(rendered) == 1
        assert signed_area(rendered[0].points) > 0
        assert is_simple_polygon(rendered[0].points)


def test_arc_precision_override_reduces_segment_count():
    points = [
        Point(0, 0),
        Point(100, 0),
        Point(100, 80),
        Point(0, 80),
    ]
    default_segments = [plan.segment_count for plan in build_arc_corner_plans(points, [5, 5, 5, 5])]
    coarse_segments = [plan.segment_count for plan in build_arc_corner_plans(points, [5, 5, 5, 5], precision=0.1)]

    assert default_arc_precision(5) == 0.001
    assert max(coarse_segments) < max(default_segments)


def test_arc_rejects_collinear_corner_with_positive_radius():
    points = [
        Point(0, 0),
        Point(5, 0),
        Point(10, 0),
        Point(10, 10),
        Point(0, 10),
    ]
    issues = validate_arc_radii(points, [0, 1, 0, 0, 0], "fillet.radii")

    assert "arc_collinear_corner" in {issue.code for issue in issues}


def test_validate_arc_reports_user_index_after_normalization():
    issues = validate_arc_radii(
        [Point(10, 0), Point(10, 10), Point(0, 10), Point(0, 0)],
        [4, 3, 2, -1],
        "fillet.radii",
        [3, 2, 1, 0],
    )

    assert issues[0].path == "fillet.radii[0]"
