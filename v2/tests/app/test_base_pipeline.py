from pathlib import Path

import pytest

from summer_gds.app.pipeline import execute_config
from summer_gds.schema.errors import ConfigError
from summer_gds.schema.yaml_v2 import parse_yaml_text


def run_config(text: str):
    config = parse_yaml_text(text, base_path=Path("/work/config.yaml"))
    return execute_config(config)


def base_yaml(vertices: str, fillet: str = "") -> str:
    return f"""
schema_version: 2
global:
  unit: um
  dbu: 0.001
shapes:
  - type: base_shape
    sid: 0
    name: shape
    layer: [1, 0]
    source:
      vertices: {vertices}
{fillet}
"""


@pytest.mark.parametrize(
    "vertices",
    [
        "[[0, 0], [100, 0], [100, 80], [0, 80]]",
        "[[0, 0], [80, 0], [80, 30], [40, 15], [0, 30]]",
        "[[0, 0], [100, 0], [101, 50], [100, 100], [0, 100]]",
        "[[0, 0], [120, 0], [120, 20], [100, 22], [0, 20]]",
    ],
)
def test_base_shape_accepts_common_convex_concave_sharp_and_obtuse_inputs(vertices):
    results = run_config(base_yaml(vertices, "    fillet:\n      radius: 0\n"))

    assert len(results) == 1
    assert results[0].canonical_boundary is not None
    assert len(results[0].output_regions) == 1
    assert not results[0].output_regions[0].region.is_empty()


def test_base_fillet_outputs_more_points_but_canonical_boundary_stays_prefillet():
    results = run_config(base_yaml("[[0, 0], [100, 0], [100, 80], [0, 80]]", "    fillet:\n      radius: 2\n"))
    result = results[0]

    assert result.canonical_boundary is not None
    assert len(result.canonical_boundary.points) == 4
    assert result.output_regions[0].metadata.role == "base_output"
    assert result.output_regions[0].metadata.point_count_before_region > 4


def test_base_ref_offset_happens_before_fillet_and_updates_canonical_boundary():
    results = run_config(
        """
schema_version: 2
global: { unit: um, dbu: 0.001 }
shapes:
  - type: base_shape
    sid: 0
    name: source
    layer: [1, 0]
    source:
      vertices: [[0, 0], [100, 0], [100, 80], [0, 80]]
  - type: base_shape
    sid: 1
    name: margin
    layer: [2, 0]
    source:
      ref: 0
      offset: 10
    fillet:
      radius: 2
"""
    )

    boundary = results[1].canonical_boundary
    assert boundary is not None
    xs = {round(point.x, 6) for point in boundary.points}
    ys = {round(point.y, 6) for point in boundary.points}
    assert xs == {-10, 110}
    assert ys == {-10, 90}
    assert results[1].output_regions[0].metadata.point_count_before_region > len(boundary.points)


def test_rejects_self_intersecting_hourglass_topology():
    with pytest.raises(ConfigError) as exc_info:
        run_config(base_yaml("[[0, 0], [100, 100], [0, 100], [100, 0]]"))

    assert "invalid_boundary" in {issue.code for issue in exc_info.value.issues}


def test_rejects_positive_fillet_on_collinear_corner():
    with pytest.raises(ConfigError) as exc_info:
        run_config(base_yaml("[[0, 0], [50, 0], [100, 0], [100, 80], [0, 80]]", "    fillet:\n      radius: 2\n"))

    assert "fillet_collinear_corner" in {issue.code for issue in exc_info.value.issues}
