from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pya

from summer_gds.model.protocol import LayerSpec, Point


@dataclass(frozen=True)
class GeometryContext:
    unit: Literal["um"]
    dbu: float


@dataclass(frozen=True)
class BoundaryMetadata:
    owner_sid: int
    source_sid: int | None
    role: str
    coordinate_unit: str


@dataclass(frozen=True)
class BoundaryObject:
    points: tuple[Point, ...]
    metadata: BoundaryMetadata


@dataclass(frozen=True)
class RegionMetadata:
    owner_sid: int
    role: str
    source_sid: int | None
    point_count_before_region: int = 0


@dataclass
class RegionObject:
    region: pya.Region
    layer: LayerSpec
    metadata: RegionMetadata


@dataclass(frozen=True)
class ShapeResult:
    sid: int
    name: str
    shape_type: str
    layer: LayerSpec
    canonical_boundary: BoundaryObject | None
    output_regions: tuple[RegionObject, ...]
