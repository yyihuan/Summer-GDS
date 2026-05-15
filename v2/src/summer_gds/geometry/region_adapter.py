from __future__ import annotations

import math

import pya

from summer_gds.geometry.primitives import normalize_counterclockwise
from summer_gds.model.geometry import (
    BoundaryMetadata,
    BoundaryObject,
    GeometryContext,
    RegionMetadata,
    RegionObject,
)
from summer_gds.model.protocol import LayerSpec, Point
from summer_gds.schema.errors import ConfigError, issue


def um_to_dbu(value_um: float, context: GeometryContext) -> int:
    scaled = value_um / context.dbu
    if scaled >= 0:
        return int(math.floor(scaled + 0.5))
    return int(math.ceil(scaled - 0.5))


def dbu_to_um(value_dbu: int, context: GeometryContext) -> float:
    return value_dbu * context.dbu


def boundary_to_region(
    boundary: BoundaryObject,
    layer: LayerSpec,
    context: GeometryContext,
    role: str,
) -> RegionObject:
    db_points = [pya.Point(um_to_dbu(point.x, context), um_to_dbu(point.y, context)) for point in boundary.points]
    polygon = pya.Polygon(db_points)
    region = pya.Region(polygon)
    return RegionObject(
        region=region,
        layer=layer,
        metadata=RegionMetadata(
            owner_sid=boundary.metadata.owner_sid,
            role=role,
            source_sid=boundary.metadata.source_sid,
            point_count_before_region=len(boundary.points),
        ),
    )


def region_to_boundary(region_object: RegionObject, context: GeometryContext, role: str) -> BoundaryObject:
    merged = region_object.region.merged()
    polygons = list(merged.each())
    if len(polygons) != 1 or polygons[0].holes() != 0:
        raise ConfigError(
            [
                issue(
                    "offset_multiple_boundaries",
                    "$.shapes",
                    "Region cannot be converted back to a single BoundaryObject.",
                )
            ]
        )
    points = tuple(
        Point(x=dbu_to_um(point.x, context), y=dbu_to_um(point.y, context))
        for point in polygons[0].each_point_hull()
    )
    points = normalize_counterclockwise(points)
    return BoundaryObject(
        points=points,
        metadata=BoundaryMetadata(
            owner_sid=region_object.metadata.owner_sid,
            source_sid=region_object.metadata.source_sid,
            role=role,
            coordinate_unit=context.unit,
        ),
    )


def clone_region_object(region_object: RegionObject) -> RegionObject:
    return RegionObject(
        region=region_object.region.dup(),
        layer=region_object.layer,
        metadata=region_object.metadata,
    )
