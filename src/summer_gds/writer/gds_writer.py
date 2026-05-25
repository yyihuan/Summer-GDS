from __future__ import annotations

from pathlib import Path

import pya

from summer_gds.model.geometry import RegionObject


def write_gds(regions: tuple[RegionObject, ...], output_path: Path, top_cell: str, dbu: float) -> None:
    if not regions:
        raise ValueError("No regions to write.")
    layout = pya.Layout()
    layout.dbu = float(dbu)
    cell = layout.create_cell(top_cell)
    for region_object in regions:
        layer_index = layout.layer(region_object.layer.layer, region_object.layer.datatype)
        cell.shapes(layer_index).insert(region_object.region)
    layout.write(str(output_path))
