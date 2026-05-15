from __future__ import annotations

import pya

from summer_gds.geometry.fillet import apply_fillet
from summer_gds.geometry.primitives import (
    EPSILON,
    has_consecutive_duplicate_points,
    is_simple_polygon,
    normalize_counterclockwise,
    signed_area,
)
from summer_gds.geometry.region_adapter import boundary_to_region, region_to_boundary, um_to_dbu
from summer_gds.model.geometry import BoundaryMetadata, BoundaryObject, GeometryContext, ShapeResult
from summer_gds.model.protocol import BaseShapeSpec, ConfigSpec, Point
from summer_gds.schema.errors import ConfigError, issue


def execute_config(config: ConfigSpec) -> tuple[ShapeResult, ...]:
    context = GeometryContext(unit=config.global_config.unit, dbu=config.global_config.dbu)
    results: list[ShapeResult] = []
    by_sid: dict[int, ShapeResult] = {}
    for shape in config.shapes:
        if shape.type != "base_shape":
            raise ConfigError([issue("unsupported_shape_pipeline", f"$.shapes[{shape.sid}]", "Only base_shape is implemented in this phase.")])
        result = _execute_base_shape(shape, by_sid, context)
        results.append(result)
        by_sid[result.sid] = result
    return tuple(results)


def _execute_base_shape(shape: BaseShapeSpec, by_sid: dict[int, ShapeResult], context: GeometryContext) -> ShapeResult:
    canonical_boundary = _resolve_source_boundary(shape, by_sid, context)
    filleted_boundary = apply_fillet(canonical_boundary, shape.fillet)
    output_region = boundary_to_region(filleted_boundary, shape.layer, context, role="base_output")
    return ShapeResult(
        sid=shape.sid,
        name=shape.name,
        shape_type=shape.type,
        layer=shape.layer,
        canonical_boundary=canonical_boundary,
        output_regions=(output_region,),
    )


def _resolve_source_boundary(shape: BaseShapeSpec, by_sid: dict[int, ShapeResult], context: GeometryContext) -> BoundaryObject:
    if shape.source.vertices is not None:
        points = normalize_counterclockwise(tuple(shape.source.vertices))
        _validate_boundary(points, shape.sid)
        return BoundaryObject(
            points=points,
            metadata=BoundaryMetadata(owner_sid=shape.sid, source_sid=None, role="source", coordinate_unit=context.unit),
        )

    source = by_sid[shape.source.ref]
    if source.canonical_boundary is None:
        raise ConfigError([issue("source_ref_not_boundary_capable", f"$.shapes[{shape.sid}].source.ref", "source.ref must resolve to a canonical boundary.")])
    boundary = BoundaryObject(
        points=source.canonical_boundary.points,
        metadata=BoundaryMetadata(owner_sid=shape.sid, source_sid=source.sid, role="source", coordinate_unit=context.unit),
    )
    if shape.source.offset is None:
        return boundary

    temp_region = boundary_to_region(boundary, shape.layer, context, role="base_offset")
    offset_dbu = um_to_dbu(shape.source.offset, context)
    offset_region = temp_region.region.dup().sized(offset_dbu)
    if offset_region.is_empty():
        raise ConfigError([issue("offset_empty_region", f"$.shapes[{shape.sid}].source.offset", "offset produced an empty region.")])
    temp_region.region = offset_region
    offset_boundary = region_to_boundary(temp_region, context, role="base_offset")
    _validate_boundary(offset_boundary.points, shape.sid)
    return offset_boundary


def _validate_boundary(points: tuple[Point, ...], sid: int) -> None:
    if len(points) < 3 or abs(signed_area(points)) <= EPSILON:
        raise ConfigError([issue("invalid_boundary", f"$.shapes[{sid}].source.vertices", "boundary must have non-zero area.")])
    if has_consecutive_duplicate_points(points):
        raise ConfigError([issue("invalid_boundary", f"$.shapes[{sid}].source.vertices", "boundary has duplicate consecutive points.")])
    if not is_simple_polygon(points):
        raise ConfigError([issue("invalid_boundary", f"$.shapes[{sid}].source.vertices", "boundary is self-intersecting.")])
