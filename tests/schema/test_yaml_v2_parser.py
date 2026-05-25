from pathlib import Path

import pytest

from summer_gds.schema.errors import ConfigError
from summer_gds.schema.yaml_v2 import parse_yaml_text


def parse(text: str):
    return parse_yaml_text(text, base_path=Path("/work/config.yaml"))


VALID_BASE = """
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


def assert_code(text: str, code: str):
    with pytest.raises(ConfigError) as exc_info:
        parse(text)
    assert code in {issue.code for issue in exc_info.value.issues}


def test_valid_base_vertices_without_gds_output_parses_for_protocol_validate():
    config = parse(VALID_BASE)

    assert config.schema_version == 2
    assert config.global_config.unit == "um"
    assert config.global_config.dbu == 0.001
    assert config.gds is None
    assert config.shapes[0].sid == 0
    assert config.shapes[0].source.vertices[2].x == 100


def test_valid_base_ref_offset_parses_and_refers_to_previous_base_shape():
    config = parse(
        VALID_BASE
        + """
  - type: base_shape
    sid: 1
    name: margin
    layer: [2, 0]
    source:
      ref: 0
      offset: 10
"""
    )

    assert config.shapes[1].source.ref == 0
    assert config.shapes[1].source.offset == 10


def test_valid_via_and_rings_parse():
    config = parse(
        VALID_BASE
        + """
  - type: via
    sid: 2
    name: contact
    layer: [10, 0]
    source:
      ref: 0
    offsets:
      inner: -5
      outer: 8
    fillet:
      inner: { radius: 1 }
      outer: { radius: 2 }
  - type: rings
    sid: 3
    name: guard
    layer: [20, 0]
    source:
      ref: 0
    count: 2
    pitch: 12
    width: 4
    fillet:
      rings:
        - inner: { radius: 1 }
          outer: { radius: 2 }
        - inner: { radius: 1 }
          outer: { radius: 2 }
"""
    )

    assert [shape.type for shape in config.shapes] == ["base_shape", "via", "rings"]
    assert config.shapes[2].count == 2
    assert len(config.shapes[2].fillet.rings) == 2


def test_rejects_duplicate_sid():
    assert_code(
        VALID_BASE
        + """
  - type: base_shape
    sid: 0
    name: duplicate
    layer: [2, 0]
    source:
      vertices: [[0, 0], [10, 0], [0, 10]]
""",
        "duplicate_sid",
    )


def test_rejects_forward_ref_and_ref_to_non_base_shape():
    assert_code(
        """
schema_version: 2
global: { unit: um, dbu: 0.001 }
shapes:
  - type: base_shape
    sid: 0
    name: bad
    layer: [1, 0]
    source:
      ref: 1
  - type: base_shape
    sid: 1
    name: later
    layer: [1, 0]
    source:
      vertices: [[0, 0], [10, 0], [0, 10]]
""",
        "source_ref_not_found_or_not_ready",
    )
    assert_code(
        VALID_BASE
        + """
  - type: via
    sid: 2
    name: contact
    layer: [10, 0]
    source: { ref: 0 }
    offsets: { inner: -1, outer: 1 }
  - type: base_shape
    sid: 3
    name: bad_ref
    layer: [3, 0]
    source: { ref: 2 }
""",
        "source_ref_not_boundary_capable",
    )


def test_rejects_non_finite_and_bool_numbers():
    assert_code(VALID_BASE.replace("[100, 0]", "[.inf, 0]"), "non_finite_number")
    assert_code(VALID_BASE.replace("sid: 0", "sid: true"), "invalid_type")


def test_rejects_dbu_and_precision_mismatch():
    assert_code(VALID_BASE.replace("dbu: 0.001", "dbu: 2.0"), "dbu_out_of_range")
    assert_code(
        VALID_BASE.replace(
            "dbu: 0.001",
            "dbu: 0.003\n  precision: 0.01",
        ),
        "precision_dbu_mismatch",
    )


def test_rejects_invalid_rings_count_pitch_width_and_fillet_length():
    invalid = (
        VALID_BASE
        + """
  - type: rings
    sid: 3
    name: guard
    layer: [20, 0]
    source: { ref: 0 }
    count: 0
    pitch: 12
    width: 4
"""
    )
    assert_code(invalid, "invalid_rings_count")
    assert_code(invalid.replace("count: 0", "count: 2").replace("pitch: 12", "pitch: 3"), "invalid_ring_pitch_width")
    assert_code(
        invalid.replace("count: 0", "count: 2")
        + """
    fillet:
      rings:
        - inner: { radius: 1 }
          outer: { radius: 2 }
""",
        "fillet_rings_length_mismatch",
    )


def test_rejects_unknown_and_forbidden_fields():
    assert_code(VALID_BASE.replace("shapes:", "outputs: []\nshapes:"), "unknown_field")
    assert_code(VALID_BASE.replace("name: source", "name: source\n    inner: {}"), "unknown_field")


def test_rejects_non_mapping_or_deep_yaml():
    assert_code("- just\n- a\n- list\n", "invalid_root")
    deep = "schema_version: 2\nglobal: { unit: um, dbu: 0.001 }\nshapes:\n" + "  - " + "{a:" * 40 + " 1" + "}" * 40
    assert_code(deep, "yaml_too_deep")
