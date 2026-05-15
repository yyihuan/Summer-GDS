from pathlib import Path

import pytest

from summer_gds.app.pipeline import execute_config
from summer_gds.schema.errors import ConfigError
from summer_gds.schema.yaml_v2 import parse_yaml_text


BASE = """
schema_version: 2
global:
  unit: um
  dbu: 0.001
shapes:
  - type: base_shape
    sid: 0
    name: source
    layer: [1, 0]
    source:
      vertices: [[0, 0], [100, 0], [100, 80], [0, 80]]
"""


def run_config(text: str):
    return execute_config(parse_yaml_text(text, base_path=Path("/work/config.yaml")))


def bbox_tuple(region_object):
    box = region_object.region.bbox()
    return (box.left, box.bottom, box.right, box.top)


def test_via_outputs_single_boolean_region_and_no_canonical_boundary():
    results = run_config(
        BASE
        + """
  - type: via
    sid: 2
    name: contact
    layer: [10, 0]
    source: { ref: 0 }
    offsets:
      inner: -5
      outer: 8
    fillet:
      inner: { radius: 1 }
      outer: { radius: 2 }
"""
    )

    via = results[1]
    assert via.canonical_boundary is None
    assert len(via.output_regions) == 1
    assert via.output_regions[0].metadata.role == "via_output"
    assert not via.output_regions[0].region.is_empty()
    assert via.output_regions[0].region.area() > 0


def test_via_inner_bigger_than_outer_reports_empty_boolean():
    with pytest.raises(ConfigError) as exc_info:
        run_config(
            BASE
            + """
  - type: via
    sid: 2
    name: bad_contact
    layer: [10, 0]
    source: { ref: 0 }
    offsets:
      inner: 10
      outer: -5
"""
        )

    assert "boolean_empty_region" in {issue.code for issue in exc_info.value.issues}


def test_rings_output_count_and_offsets_match_protocol():
    results = run_config(
        BASE
        + """
  - type: rings
    sid: 3
    name: guard
    layer: [20, 0]
    source: { ref: 0 }
    count: 3
    pitch: 12
    width: 4
"""
    )

    rings = results[1]
    assert rings.canonical_boundary is None
    assert [region.metadata.role for region in rings.output_regions] == ["ring_output", "ring_output", "ring_output"]
    assert [bbox_tuple(region) for region in rings.output_regions] == [
        (-4000, -4000, 104000, 84000),
        (-16000, -16000, 116000, 96000),
        (-28000, -28000, 128000, 108000),
    ]


def test_rings_without_fillet_keeps_outer_boundaries_unfilleted():
    results = run_config(
        BASE
        + """
  - type: rings
    sid: 3
    name: guard
    layer: [20, 0]
    source: { ref: 0 }
    count: 2
    pitch: 12
    width: 4
"""
    )

    rings = results[1]
    assert [region.metadata.point_count_before_region for region in rings.output_regions] == [8, 8]


def test_rings_with_per_ring_fillet_increases_boundary_point_count():
    results = run_config(
        BASE
        + """
  - type: rings
    sid: 3
    name: guard
    layer: [20, 0]
    source: { ref: 0 }
    count: 1
    pitch: 12
    width: 4
    fillet:
      rings:
        - inner: { radius: 1 }
          outer: { radius: 2 }
"""
    )

    rings = results[1]
    assert rings.output_regions[0].metadata.point_count_before_region > 8
