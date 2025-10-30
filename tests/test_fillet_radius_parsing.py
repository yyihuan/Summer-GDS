import pytest
import importlib.util
from pathlib import Path

from .output_utils import record_snapshot

MODULE_PATH = Path(__file__).resolve().parents[1] / "gds_utils" / "fillet_utils.py"
spec = importlib.util.spec_from_file_location("fillet_utils_for_test", MODULE_PATH)
fillet_utils = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(fillet_utils)

normalize_arc_fillet_config = fillet_utils.normalize_arc_fillet_config


def _build_config(radius_field):
    config = {
        "type": "arc",
        "precision": 0.01,
        "interactive": False,
    }
    config.update(radius_field)
    return config


def test_normalize_scalar_radius_expands():
    fillet_config = _build_config({"radius": 1.5})
    normalized = normalize_arc_fillet_config("demo_shape", fillet_config, vertex_count=4)
    record_snapshot(
        "fillet_radius_parsing",
        "scalar_radius",
        {
            "input_yaml": """
shapes:
  - name: demo_shape
    type: rings
    ring_num: 1
    vertices: 0,0;10,0;10,10;0,10
    fillet:
      type: arc
      radius: 1.5
""".strip(),
            "normalized_radius_list": normalized["radius_list"],
        },
    )
    assert normalized["radius_list"] == [1.5, 1.5, 1.5, 1.5]
    assert "radius" not in normalized


def test_normalize_radius_list_kept_when_matching_vertices():
    fillet_config = _build_config({"radius_list": [0.8, 0.9, 1.0, 1.1]})
    normalized = normalize_arc_fillet_config("quad", fillet_config, vertex_count=4)
    record_snapshot(
        "fillet_radius_parsing",
        "explicit_radius_list",
        {
            "input_yaml": """
shapes:
  - name: quad
    type: polygon
    vertices: 0,0;10,0;10,10;0,10
    fillet:
      type: arc
      radius_list: [0.8, 0.9, 1.0, 1.1]
""".strip(),
            "normalized_radius_list": normalized["radius_list"],
        },
    )
    assert normalized["radius_list"] == [0.8, 0.9, 1.0, 1.1]


def test_normalize_ring_specific_length_pass_through():
    fillet_config = _build_config({"radius_list": [0.5] * 12})
    normalized = normalize_arc_fillet_config("ring", fillet_config, vertex_count=4, ring_num_hint=3)
    record_snapshot(
        "fillet_radius_parsing",
        "ring_specific_radius_list",
        {
            "input_yaml": """
shapes:
  - name: ring
    type: rings
    ring_num: 3
    vertices: 0,0;10,0;10,10;0,10
    fillet:
      type: arc
      radius_list: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
""".strip(),
            "normalized_radius_list_len": len(normalized["radius_list"]),
        },
    )
    assert len(normalized["radius_list"]) == 12


def test_normalize_ring_explicit_inner_outer_pass_through():
    explicit_list = [0.5] * 12 + [0.6] * 12
    fillet_config = _build_config({"radius_list": explicit_list})
    normalized = normalize_arc_fillet_config("ring_explicit", fillet_config, vertex_count=4, ring_num_hint=3)
    record_snapshot(
        "fillet_radius_parsing",
        "ring_explicit_radius_list",
        {
            "input_yaml": """
shapes:
  - name: ring_explicit
    type: rings
    ring_num: 3
    vertices: 0,0;10,0;10,10;0,10
    fillet:
      type: arc
      radius_list: [0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6]
""".strip(),
            "normalized_radius_list_len": len(normalized["radius_list"]),
        },
    )
    assert len(normalized["radius_list"]) == 24


def test_normalize_invalid_length_raises():
    fillet_config = _build_config({"radius_list": [0.5, 0.6, 0.7]})
    with pytest.raises(ValueError) as excinfo:
        normalize_arc_fillet_config("bad_shape", fillet_config, vertex_count=4)

    record_snapshot(
        "fillet_radius_parsing",
        "invalid_length",
        {
            "input_yaml": """
shapes:
  - name: bad_shape
    type: polygon
    vertices: 0,0;10,0;10,10;0,10
    fillet:
      type: arc
      radius_list: [0.5, 0.6, 0.7]
""".strip(),
            "error": str(excinfo.value),
        },
    )
