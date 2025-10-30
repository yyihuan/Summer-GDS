import importlib.util
from pathlib import Path

from .output_utils import record_snapshot

MODULE_PATH = Path(__file__).resolve().parents[1] / "gds_utils" / "fillet_utils.py"
spec = importlib.util.spec_from_file_location("fillet_utils_for_via_test", MODULE_PATH)
fillet_utils = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(fillet_utils)

normalize_arc_fillet_config = fillet_utils.normalize_arc_fillet_config
resolve_via_fillet_configs = fillet_utils.resolve_via_fillet_configs


def test_resolve_via_shared_radius():
    fillet_config = normalize_arc_fillet_config(
        "via_shared",
        {
            "type": "arc",
            "precision": 0.01,
            "interactive": False,
            "radius_list": [1.0, 1.0, 1.0, 1.0],
        },
        vertex_count=4,
        allow_inner_outer_split=True,
    )

    base_config, inner_config, outer_config = resolve_via_fillet_configs(
        "via_shared",
        fillet_config,
        base_radius_list=[1.0, 1.0, 1.0, 1.0],
        zoom_delta=2.0,
    )

    record_snapshot(
        "via_radius_series",
        "shared_radius_config",
        {
            "input_yaml": """
shape:
  name: via_shared
  type: via
  vertices: 0,0;10,0;10,10;0,10
  inner_zoom: -1.0
  outer_zoom: 1.5
  fillet:
    type: arc
    radius_list: [1.0, 1.0, 1.0, 1.0]
""".strip(),
            "base_config": base_config,
            "inner_config": inner_config,
            "outer_config": outer_config,
        },
    )

    assert inner_config is None
    assert outer_config is None
    assert base_config["radius_list"] == [1.0, 1.0, 1.0, 1.0]
    assert "preserve_radius_list" not in base_config


def test_resolve_via_explicit_inner_outer():
    fillet_config = normalize_arc_fillet_config(
        "via_explicit",
        {
            "type": "arc",
            "precision": 0.01,
            "interactive": False,
            "radius_list": [0.5, 0.6, 0.7, 0.8, 1.5, 1.6, 1.7, 1.8],
        },
        vertex_count=4,
        allow_inner_outer_split=True,
    )

    base_config, inner_config, outer_config = resolve_via_fillet_configs(
        "via_explicit",
        fillet_config,
        base_radius_list=[0.5, 0.6, 0.7, 0.8],
        zoom_delta=3.0,
    )

    record_snapshot(
        "via_radius_series",
        "explicit_inner_outer_config",
        {
            "input_yaml": """
shape:
  name: via_explicit
  type: via
  vertices: 0,0;10,0;10,10;0,10
  inner_zoom: -1.0
  outer_zoom: 2.0
  fillet:
    type: arc
    radius_list: [0.5, 0.6, 0.7, 0.8, 1.5, 1.6, 1.7, 1.8]
""".strip(),
            "base_config": base_config,
            "inner_config": inner_config,
            "outer_config": outer_config,
        },
    )

    assert base_config is None
    assert inner_config is not None and outer_config is not None
    assert inner_config["radius_list"] == [0.5, 0.6, 0.7, 0.8]
    assert outer_config["radius_list"] == [1.5, 1.6, 1.7, 1.8]
    assert inner_config["preserve_radius_list"] is True
    assert outer_config["preserve_radius_list"] is True


def test_resolve_via_custom_short_list_generates_outer():
    fillet_config = normalize_arc_fillet_config(
        "via_custom",
        {
            "type": "arc",
            "precision": 0.01,
            "interactive": False,
            "radius_list": [1.5, 1.2, 0.8, 2.5],
        },
        vertex_count=4,
        allow_inner_outer_split=True,
    )

    base_config, inner_config, outer_config = resolve_via_fillet_configs(
        "via_custom",
        fillet_config,
        base_radius_list=[1.0, 1.0, 1.0, 2.0],
        zoom_delta=2.0,
    )

    record_snapshot(
        "via_radius_series",
        "custom_short_list_config",
        {
            "input_yaml": """
shape:
  name: via_custom
  type: via
  vertices: 0,0;10,0;10,10;0,10
  inner_zoom: -1.0
  outer_zoom: 1.0
  fillet:
    type: arc
    radius_list: [1.5, 1.2, 0.8, 2.5]
""".strip(),
            "base_config": base_config,
            "inner_config": inner_config,
            "outer_config": outer_config,
        },
    )

    assert base_config is None
    assert inner_config is not None and outer_config is not None
    assert inner_config["radius_list"] == [1.5, 1.2, 0.8, 2.5]
    assert outer_config["radius_list"] == [3.5, 3.2, 2.8, 4.5]
    assert inner_config["preserve_radius_list"] is True
    assert outer_config["preserve_radius_list"] is True
