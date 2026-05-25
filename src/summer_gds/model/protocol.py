from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class LayerSpec:
    layer: int
    datatype: int = 0


@dataclass(frozen=True)
class GlobalSpec:
    unit: Literal["um"]
    dbu: float
    precision: float | None = None


@dataclass(frozen=True)
class GdsSpec:
    top_cell: str | None = None
    output: Path | None = None


@dataclass(frozen=True)
class SourceSpec:
    vertices: tuple[Point, ...] | None = None
    ref: int | None = None
    offset: float | None = None


@dataclass(frozen=True)
class RadiusSpec:
    radius: float | None = None
    radii: tuple[float, ...] | None = None
    precision: float | None = None


@dataclass(frozen=True)
class ViaOffsets:
    inner: float
    outer: float


@dataclass(frozen=True)
class ViaFilletSpec:
    inner: RadiusSpec | None = None
    outer: RadiusSpec | None = None


@dataclass(frozen=True)
class RingFilletSpec:
    inner: RadiusSpec | None = None
    outer: RadiusSpec | None = None


@dataclass(frozen=True)
class RingsFilletSpec:
    rings: tuple[RingFilletSpec, ...] | None = None


@dataclass(frozen=True)
class ShapeSpec:
    type: str
    sid: int
    name: str
    layer: LayerSpec
    source: SourceSpec
    fillet: RadiusSpec | ViaFilletSpec | RingsFilletSpec | None


@dataclass(frozen=True)
class BaseShapeSpec(ShapeSpec):
    pass


@dataclass(frozen=True)
class ViaSpec(ShapeSpec):
    offsets: ViaOffsets


@dataclass(frozen=True)
class RingsSpec(ShapeSpec):
    count: int
    pitch: float
    width: float


@dataclass(frozen=True)
class ConfigSpec:
    schema_version: int
    global_config: GlobalSpec
    gds: GdsSpec | None
    shapes: tuple[ShapeSpec, ...]
    base_path: Path
