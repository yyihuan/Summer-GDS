import pytest
import importlib.util
from pathlib import Path
import sys
import types

if "klayout.db" not in sys.modules:
    klayout_stub = types.ModuleType("klayout")
    klayout_db_stub = types.ModuleType("klayout.db")

    class _DummyRegion:
        def __init__(self):
            self._items = []

        def __iadd__(self, other):
            self._items.append(other)
            return self

        def is_empty(self):
            return len(self._items) == 0

        def count(self):
            return len(self._items)

    class _DummyDPoint:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class _DummyDPolygon:
        def __init__(self, points):
            self._points = points

        def each_point_hull(self):
            return self._points

    klayout_db_stub.Region = _DummyRegion
    klayout_db_stub.DPoint = _DummyDPoint
    klayout_db_stub.DPolygon = _DummyDPolygon
    klayout_stub.db = klayout_db_stub
    sys.modules.setdefault("klayout", klayout_stub)
    sys.modules.setdefault("klayout.db", klayout_db_stub)

from .output_utils import record_snapshot

MODULE_PATH = Path(__file__).resolve().parents[1] / "gds_utils" / "ring_utils.py"
spec = importlib.util.spec_from_file_location("ring_utils_for_test", MODULE_PATH)
ring_utils = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(ring_utils)

build_ring_radius_series = ring_utils.build_ring_radius_series
Frame = None
Region = None


def _lazy_load_region_dependencies():
    global Frame, Region
    if Frame is None or Region is None:
        from gds_utils.frame import Frame as _Frame
        from gds_utils.region import Region as _Region
        Frame = _Frame
        Region = _Region


@pytest.fixture
def zoom_defaults():
    return {
        "vertex_count": 4,
        "base_zoom": 0.0,
        "inner_adjust": 0.0,
        "outer_adjust": 0.0,
    }


def test_custom_mode_repeat_base(zoom_defaults):
    series = build_ring_radius_series(
        mode="custom",
        base_radius_list=[1.0, 1.0, 1.0, 1.0],
        ring_width_list=[2.0, 2.0],
        ring_space_list=[1.0, 1.0],
        zoom_params=zoom_defaults,
        ring_num=2,
    )
    record_snapshot(
        "ring_radius_series",
        "custom_repeat",
        {
            "input_yaml": """
ring_mode: custom
base_radius_list: [1.0, 1.0, 1.0, 1.0]
ring_width_list: [2.0, 2.0]
ring_space_list: [1.0, 1.0]
zoom_params:
  vertex_count: 4
  base_zoom: 0.0
  inner_adjust: 0.0
  outer_adjust: 0.0
ring_num: 2
""".strip(),
            "series": series,
        },
    )
    assert series == [[1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0]]


def test_custom_mode_per_ring_values(zoom_defaults):
    series = build_ring_radius_series(
        mode="custom",
        base_radius_list=[1.0, 1.2, 1.4, 1.6, 0.8, 0.9, 1.0, 1.1],
        ring_width_list=[2.0, 2.0],
        ring_space_list=[0.5, 0.5],
        zoom_params=zoom_defaults,
        ring_num=2,
    )
    record_snapshot(
        "ring_radius_series",
        "custom_per_ring",
        {
            "input_yaml": """
ring_mode: custom
base_radius_list: [1.0, 1.2, 1.4, 1.6, 0.8, 0.9, 1.0, 1.1]
ring_width_list: [2.0, 2.0]
ring_space_list: [0.5, 0.5]
zoom_params:
  vertex_count: 4
  base_zoom: 0.0
  inner_adjust: 0.0
  outer_adjust: 0.0
ring_num: 2
""".strip(),
            "series": series,
        },
    )
    assert series == [
        [1.0, 1.2, 1.4, 1.6],
        [0.8, 0.9, 1.0, 1.1],
    ]


def test_custom_mode_invalid_length_raises(zoom_defaults):
    with pytest.raises(ValueError) as excinfo:
        build_ring_radius_series(
            mode="custom",
            base_radius_list=[1.0, 1.1, 1.2],
            ring_width_list=[2.0, 2.0],
            ring_space_list=[1.0, 1.0],
            zoom_params=zoom_defaults,
            ring_num=2,
        )
    record_snapshot(
        "ring_radius_series",
        "custom_invalid_length",
        {
            "input_yaml": """
ring_mode: custom
base_radius_list: [1.0, 1.1, 1.2]
ring_width_list: [2.0, 2.0]
ring_space_list: [1.0, 1.0]
zoom_params:
  vertex_count: 4
  base_zoom: 0.0
  inner_adjust: 0.0
  outer_adjust: 0.0
ring_num: 2
""".strip(),
            "error": str(excinfo.value),
        },
    )


def test_concentric_mode_accumulates_offsets(zoom_defaults):
    zoom_defaults.update({"inner_adjust": -0.5, "outer_adjust": 0.75})
    series = build_ring_radius_series(
        mode="concentric",
        base_radius_list=[0.5, 0.6, 0.7, 0.8],
        ring_width_list=[3.0, 4.0],
        ring_space_list=[2.0, 1.0],
        zoom_params=zoom_defaults,
        ring_num=2,
    )
    offsets = []
    offset_accumulator = 0.0
    widths = [3.0, 4.0]
    spaces = [2.0, 1.0]
    for idx in range(2):
        baseline_inner = offset_accumulator - zoom_defaults["base_zoom"]
        baseline_outer = baseline_inner + widths[idx]
        inner_offset = baseline_inner + zoom_defaults["inner_adjust"]
        outer_offset = baseline_outer + zoom_defaults["outer_adjust"]
        offsets.append({
            "inner_offset": inner_offset,
            "outer_offset": outer_offset,
        })
        offset_accumulator += widths[idx] + spaces[idx]

    record_snapshot(
        "ring_radius_series",
        "concentric_offsets",
        {
            "input_yaml": """
ring_mode: concentric
base_radius_list: [0.5, 0.6, 0.7, 0.8]
ring_width_list: [3.0, 4.0]
ring_space_list: [2.0, 1.0]
zoom_params:
  vertex_count: 4
  base_zoom: 0.0
  inner_adjust: -0.5
  outer_adjust: 0.75
ring_num: 2
""".strip(),
            "series": series,
            "computed_offsets": offsets,
        },
    )

    for idx, radii in enumerate(series):
        inner_offset = offsets[idx]["inner_offset"]
        outer_offset = offsets[idx]["outer_offset"]
        actual_inner = [round(val + inner_offset, 6) for val in radii]
        actual_outer = [round(val + outer_offset, 6) for val in radii]
        assert all(val >= 0 for val in actual_inner)
        assert all(val >= 0 for val in actual_outer)


def test_concentric_mode_invalid_width_raises(zoom_defaults):
    with pytest.raises(ValueError) as excinfo:
        build_ring_radius_series(
            mode="concentric",
            base_radius_list=[0.5, 0.6, 0.7, 0.8],
            ring_width_list=[0.0, 3.0],
            ring_space_list=[1.0, 1.0],
            zoom_params=zoom_defaults,
            ring_num=2,
        )
    record_snapshot(
        "ring_radius_series",
        "concentric_invalid_width",
        {
            "input_yaml": """
ring_mode: concentric
base_radius_list: [0.5, 0.6, 0.7, 0.8]
ring_width_list: [0.0, 3.0]
ring_space_list: [1.0, 1.0]
zoom_params:
  vertex_count: 4
  base_zoom: 0.0
  inner_adjust: 0.0
  outer_adjust: 0.0
ring_num: 2
""".strip(),
            "error": str(excinfo.value),
        },
    )


def test_region_create_rings_applies_series(monkeypatch):
    _lazy_load_region_dependencies()

    ring_radii_series = [
        [1.0, 1.0, 1.0, 1.0],
        [2.0, 2.0, 2.0, 2.0],
    ]

    captured = []
    preserve_flags = []

    class _DummyKdbRegion:
        def __init__(self):
            self.items = []

        def __iadd__(self, other):
            self.items.append(other)
            return self

    def _fake_init(self):
        self.kdb_region = _DummyKdbRegion()

    def _fake_polygon2ring(cls, frame, inner_zoom, outer_zoom, fillet_config=None):
        captured.append(list(fillet_config.get("radius_list", [])) if fillet_config else None)
        preserve_flags.append(fillet_config.get("preserve_radius_list"))

        dummy = types.SimpleNamespace()
        dummy.get_klayout_region = lambda: object()
        return dummy

    monkeypatch.setattr(Region, "__init__", _fake_init, raising=False)
    monkeypatch.setattr(Region, "polygon2ring", classmethod(_fake_polygon2ring))

    frame = Frame([(0, 0), (10, 0), (10, 10), (0, 10)])
    Region.create_rings(
        frame,
        ring_width=[2.0, 2.0],
        ring_space=[1.0, 1.0],
        ring_num=2,
        fillet_config={"type": "arc", "radius_list": [1.0, 1.0, 1.0, 1.0]},
        ring_radii_series=ring_radii_series,
        preserve_radius_list=True,
    )

    record_snapshot(
        "ring_radius_series",
        "region_applies_series",
        {
            "input_yaml": """
ring_mode: custom
ring_width: [2.0, 2.0]
ring_space: [1.0, 1.0]
ring_num: 2
""".strip(),
            "series": ring_radii_series,
            "captured_radius_lists": captured,
            "preserve_flags": preserve_flags,
        },
    )

    assert captured == ring_radii_series
    assert all(flag for flag in preserve_flags)
