"""Normalized domain model for the Summer-GDS MVP."""

from dataclasses import dataclass
from typing import List, Optional, Union


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def as_tuple(self):
        return (self.x, self.y)


@dataclass(frozen=True)
class Layer:
    layer: int
    datatype: int

    def as_tuple(self):
        return (self.layer, self.datatype)


@dataclass(frozen=True)
class GlobalConfig:
    dbu: float
    precision: Optional[float]


@dataclass(frozen=True)
class GdsConfig:
    output_file: str
    cell_name: str
    default_layer: Layer


@dataclass(frozen=True)
class BevelFillet:
    distances: List[float]
    mode: str = "bevel"


@dataclass(frozen=True)
class ArcFillet:
    radii: List[float]
    mode: str = "arc_v2"


@dataclass(frozen=True)
class PolygonShape:
    id: str
    name: str
    layer: Layer
    vertices: List[Point]
    vertex_user_indices: List[int]
    fillet: Optional[Union[BevelFillet, ArcFillet]]
    type: str = "base_shape"
    geometry_type: str = "polygon"


@dataclass(frozen=True)
class CircleShape:
    id: str
    name: str
    layer: Layer
    center: Point
    radius: float
    fillet: None = None
    type: str = "base_shape"
    geometry_type: str = "circle"


@dataclass(frozen=True)
class NormalizedConfig:
    schema_version: int
    global_config: GlobalConfig
    gds: GdsConfig
    shapes: List[object]


@dataclass(frozen=True)
class RenderedPolygon:
    id: str
    layer: Layer
    points: List[Point]
