from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.patches import Polygon as PolygonPatch

from summer_gds.model.geometry import RegionObject
from summer_gds.model.protocol import LayerSpec


@dataclass(frozen=True)
class ImageOutputConfig:
    path: Path
    format: Literal["png", "svg"] = "png"
    width_px: int = 1024
    height_px: int = 1024
    max_side_px: int = 4096
    padding_ratio: float = 0.05
    background: str = "#ffffff"
    transparent: bool = False
    dbu: float = 0.001
    show_axes: bool = False
    debug_overlay: bool = False


def render_image(regions: tuple[RegionObject, ...], output: ImageOutputConfig) -> None:
    if not regions:
        raise ValueError("No regions to render.")
    if max(output.width_px, output.height_px) > output.max_side_px:
        raise ValueError("Image side exceeds max_side_px.")

    bbox = _combined_bbox(regions)
    width_in = max(1, output.width_px) / 100
    height_in = max(1, output.height_px) / 100
    figure, axis = plt.subplots(figsize=(width_in, height_in), dpi=100)
    figure.patch.set_facecolor(output.background)
    axis.set_facecolor(output.background)

    for region_object in sorted(regions, key=lambda item: (item.layer.layer, item.layer.datatype)):
        color = _stable_color(region_object.layer)
        for polygon in region_object.region.each():
            points = [(point.x * output.dbu, point.y * output.dbu) for point in polygon.each_point_hull()]
            patch = PolygonPatch(points, closed=True, facecolor=color, edgecolor="#111111", linewidth=0.8, alpha=0.75)
            axis.add_patch(patch)
            for hole_index in range(polygon.holes()):
                hole = [(point.x * output.dbu, point.y * output.dbu) for point in polygon.each_point_hole(hole_index)]
                hole_patch = PolygonPatch(hole, closed=True, facecolor=output.background, edgecolor=output.background, linewidth=0)
                axis.add_patch(hole_patch)

    min_x, min_y, max_x, max_y = bbox
    pad_x = max((max_x - min_x) * output.padding_ratio, output.dbu)
    pad_y = max((max_y - min_y) * output.padding_ratio, output.dbu)
    axis.set_xlim(min_x - pad_x, max_x + pad_x)
    axis.set_ylim(min_y - pad_y, max_y + pad_y)
    axis.set_aspect("equal", adjustable="box")
    if not output.show_axes:
        axis.axis("off")
    figure.tight_layout(pad=0)
    figure.savefig(
        output.path,
        format=output.format,
        transparent=output.transparent,
        facecolor=figure.get_facecolor(),
        metadata={"Software": "summer-gds-v2"},
    )
    plt.close(figure)


def _combined_bbox(regions: tuple[RegionObject, ...]) -> tuple[float, float, float, float]:
    boxes = [region.region.bbox() for region in regions if not region.region.is_empty()]
    if not boxes:
        raise ValueError("Cannot render empty regions.")
    min_x = min(box.left for box in boxes)
    min_y = min(box.bottom for box in boxes)
    max_x = max(box.right for box in boxes)
    max_y = max(box.top for box in boxes)
    dbu = 0.001
    return min_x * dbu, min_y * dbu, max_x * dbu, max_y * dbu


def _stable_color(layer: LayerSpec) -> str:
    digest = hashlib.sha256(f"{layer.layer}:{layer.datatype}".encode("ascii")).hexdigest()
    r = 64 + int(digest[0:2], 16) % 160
    g = 64 + int(digest[2:4], 16) % 160
    b = 64 + int(digest[4:6], 16) % 160
    return f"#{r:02x}{g:02x}{b:02x}"
