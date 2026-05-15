from pathlib import Path

import pytest

from mvp_summer_gds.config.loader import load_yaml_file
from mvp_summer_gds.config.schema import normalize_config
from mvp_summer_gds.gds.writer import write_gds
from mvp_summer_gds.geometry.renderer import render_config

db = pytest.importorskip("klayout.db")

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_writer_creates_readable_gds_with_expected_cell_and_layer(tmp_path):
    config = normalize_config(load_yaml_file(FIXTURES / "valid_polygon.yaml"))
    output = tmp_path / "polygon.gds"
    write_gds(render_config(config), config.gds.cell_name, config.global_config.dbu, output)

    layout = db.Layout()
    layout.read(str(output))
    cell = layout.cell("TOP")
    assert cell is not None

    layer_index = layout.layer(db.LayerInfo(2, 0))
    assert _shape_count(cell, layer_index) == 1


def test_writer_creates_readable_arc_gds(tmp_path):
    config = normalize_config(load_yaml_file(FIXTURES / "valid_polygon_arc.yaml"))
    output = tmp_path / "arc.gds"
    write_gds(render_config(config), config.gds.cell_name, config.global_config.dbu, output)

    layout = db.Layout()
    layout.read(str(output))
    cell = layout.cell("TOP")
    assert cell is not None

    layer_index = layout.layer(db.LayerInfo(2, 0))
    assert _shape_count(cell, layer_index) == 1


def test_writer_rejects_empty_polygon_list(tmp_path):
    with pytest.raises(Exception, match="empty GDS"):
        write_gds([], "TOP", 0.001, tmp_path / "empty.gds")


def _shape_count(cell, layer_index):
    count = 0
    for _shape in cell.shapes(layer_index).each():
        count += 1
    return count
