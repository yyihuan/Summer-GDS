from pathlib import Path

import pytest

from mvp_summer_gds.config.loader import load_yaml_file
from mvp_summer_gds.config.schema import normalize_config
from mvp_summer_gds.gds.writer import write_gds
from mvp_summer_gds.geometry.renderer import render_config

db = pytest.importorskip("klayout.db")

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
VISUAL_OUTPUT = Path(__file__).resolve().parents[1] / "_visual_output"


def test_visual_gds_snapshots_are_generated_for_octagon_precision_switch():
    outputs = [
        _render_fixture_gds("valid_polygon_arc_octagon_um.yaml", "valid_polygon_arc_octagon_um.gds"),
        _render_fixture_gds("valid_polygon_arc_octagon_scaled.yaml", "valid_polygon_arc_octagon_scaled.gds"),
    ]

    for output in outputs:
        assert output.exists()
        assert output.stat().st_size > 100


def _render_fixture_gds(fixture_name, output_name):
    config = normalize_config(load_yaml_file(FIXTURES / fixture_name))
    output = VISUAL_OUTPUT / output_name
    output.parent.mkdir(parents=True, exist_ok=True)

    write_gds(render_config(config), config.gds.cell_name, config.global_config.dbu, output)

    layout = db.Layout()
    layout.read(str(output))
    assert layout.cell(config.gds.cell_name) is not None
    return output
