from mvp_summer_gds.config.loader import load_yaml_file
from mvp_summer_gds.config.schema import normalize_config
from mvp_summer_gds.geometry.corners import CornerKind, build_corner_contexts
from mvp_summer_gds.geometry.primitives import normalize_counterclockwise
from mvp_summer_gds.model import Point


def test_corner_context_preserves_user_index_for_counterclockwise_points():
    points = [
        Point(0, 0),
        Point(10, 0),
        Point(10, 10),
        Point(0, 10),
    ]
    contexts = build_corner_contexts(points, [1, 2, 3, 4])

    assert [context.user_index for context in contexts] == [0, 1, 2, 3]
    assert [context.normalized_index for context in contexts] == [0, 1, 2, 3]
    assert [context.radius for context in contexts] == [1.0, 2.0, 3.0, 4.0]
    assert {context.corner_kind for context in contexts} == {CornerKind.CONVEX}
    assert contexts[0].prev_point == Point(0, 10)
    assert contexts[0].vertex == Point(0, 0)
    assert contexts[0].next_point == Point(10, 0)
    assert contexts[0].incoming_edge == Point(0, -10)
    assert contexts[0].outgoing_edge == Point(10, 0)


def test_corner_context_preserves_user_index_after_clockwise_normalization():
    clockwise_points = [
        Point(0, 0),
        Point(0, 10),
        Point(10, 10),
        Point(10, 0),
    ]
    normalized_points, reversed_order = normalize_counterclockwise(clockwise_points)
    assert reversed_order is True

    user_indices = list(reversed(range(len(clockwise_points))))
    normalized_radii = list(reversed([1, 2, 3, 4]))
    contexts = build_corner_contexts(normalized_points, normalized_radii, user_indices)

    radius_by_user_index = {context.user_index: context.radius for context in contexts}
    assert radius_by_user_index == {0: 1.0, 1: 2.0, 2: 3.0, 3: 4.0}


def test_corner_context_classifies_concave_and_collinear_corners():
    concave_points = [
        Point(0, 0),
        Point(10, 0),
        Point(10, 10),
        Point(5, 5),
        Point(0, 10),
    ]
    concave_contexts = build_corner_contexts(concave_points)
    concave_by_vertex = {context.vertex.as_tuple(): context.corner_kind for context in concave_contexts}
    assert concave_by_vertex[(5, 5)] == CornerKind.CONCAVE

    collinear_points = [
        Point(0, 0),
        Point(5, 0),
        Point(10, 0),
        Point(10, 10),
        Point(0, 10),
    ]
    collinear_contexts = build_corner_contexts(collinear_points)
    assert collinear_contexts[1].corner_kind == CornerKind.COLLINEAR
    assert collinear_contexts[1].prev_point == Point(0, 0)
    assert collinear_contexts[1].vertex == Point(5, 0)
    assert collinear_contexts[1].next_point == Point(10, 0)


def test_normalized_polygon_shape_stores_user_indices_for_clockwise_input(tmp_path):
    config_path = tmp_path / "clockwise.yaml"
    config_path.write_text(
        """
schema_version: 1
global:
  dbu: 0.001
  precision: null
gds:
  output_file: "clockwise.gds"
  cell_name: "TOP"
  default_layer: [1, 0]
shapes:
  - id: "cw"
    type: "base_shape"
    geometry_type: "polygon"
    name: "clockwise"
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

    assert config.shapes[0].vertex_user_indices == [3, 2, 1, 0]
    assert config.shapes[0].fillet.radii == [4.0, 3.0, 2.0, 1.0]
