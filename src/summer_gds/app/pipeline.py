from __future__ import annotations

from summer_gds.geometry.fillet import apply_fillet
from summer_gds.geometry.primitives import (
    EPSILON,
    has_consecutive_duplicate_points,
    is_simple_polygon,
    normalize_counterclockwise,
    signed_area,
)
from summer_gds.geometry.region_adapter import boundary_to_region, region_to_boundary, um_to_dbu
from summer_gds.model.geometry import BoundaryMetadata, BoundaryObject, GeometryContext, RegionMetadata, RegionObject, ShapeResult
from summer_gds.model.protocol import BaseShapeSpec, ConfigSpec, LayerSpec, Point, RingsSpec, ViaSpec
from summer_gds.schema.errors import ConfigError, issue


def execute_config(config: ConfigSpec) -> tuple[ShapeResult, ...]:
    context = GeometryContext(unit=config.global_config.unit, dbu=config.global_config.dbu)
    results: list[ShapeResult] = []
    by_sid: dict[int, ShapeResult] = {}
    for shape in config.shapes:
        if shape.type == "base_shape":
            result = _execute_base_shape(shape, by_sid, context)
        elif shape.type == "via":
            result = _execute_via(shape, by_sid, context)
        elif shape.type == "rings":
            result = _execute_rings(shape, by_sid, context)
        else:
            raise ConfigError([issue("unsupported_shape_pipeline", f"$.shapes[{shape.sid}]", f"Unsupported shape type: {shape.type}")])
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

    return _resolve_ref_boundary(shape, by_sid, context)


def _resolve_ref_boundary(shape: BaseShapeSpec | ViaSpec | RingsSpec, by_sid: dict[int, ShapeResult], context: GeometryContext) -> BoundaryObject:
    source = by_sid[shape.source.ref]
    if source.canonical_boundary is None:
        raise ConfigError([issue("source_ref_not_boundary_capable", f"$.shapes[{shape.sid}].source.ref", "source.ref must resolve to a canonical boundary.")])
    boundary = BoundaryObject(
        points=source.canonical_boundary.points,
        metadata=BoundaryMetadata(owner_sid=shape.sid, source_sid=source.sid, role="source", coordinate_unit=context.unit),
    )
    if shape.source.offset is None:
        return boundary

    return _offset_boundary(boundary, shape.source.offset, shape.layer, context, "base_offset")


def _offset_boundary(
    boundary: BoundaryObject,
    offset_um: float,
    layer: LayerSpec,
    context: GeometryContext,
    role: str,
) -> BoundaryObject:
    temp_region = boundary_to_region(boundary, layer, context, role=role)
    offset_dbu = um_to_dbu(offset_um, context)
    offset_region = temp_region.region.dup().sized(offset_dbu)
    if offset_region.is_empty():
        raise ConfigError([issue("offset_empty_region", "$.shapes", "offset produced an empty region.")])
    temp_region.region = offset_region
    temp_region.layer = layer
    temp_region.metadata = RegionMetadata(
        owner_sid=boundary.metadata.owner_sid,
        role=role,
        source_sid=boundary.metadata.source_sid,
        point_count_before_region=len(boundary.points),
    )
    offset_boundary = region_to_boundary(temp_region, context, role=role)
    _validate_boundary(offset_boundary.points, boundary.metadata.owner_sid)
    return offset_boundary


def _execute_via(shape: ViaSpec, by_sid: dict[int, ShapeResult], context: GeometryContext) -> ShapeResult:
    source_boundary = _resolve_shape_source_boundary(shape, by_sid, context)
    inner = _offset_boundary(source_boundary, shape.offsets.inner, shape.layer, context, "via_inner")
    outer = _offset_boundary(source_boundary, shape.offsets.outer, shape.layer, context, "via_outer")
    inner_fillet = shape.fillet.inner if shape.fillet else None
    outer_fillet = shape.fillet.outer if shape.fillet else None
    inner = apply_fillet(inner, inner_fillet)
    outer = apply_fillet(outer, outer_fillet)
    inner_region = boundary_to_region(inner, shape.layer, context, role="via_inner")
    outer_region = boundary_to_region(outer, shape.layer, context, role="via_outer")
    final_region = outer_region.region.dup() - inner_region.region
    if final_region.is_empty():
        raise ConfigError([issue("boolean_empty_region", f"$.shapes[{shape.sid}]", "via boolean result is empty.")])
    return ShapeResult(
        sid=shape.sid,
        name=shape.name,
        shape_type=shape.type,
        layer=shape.layer,
        canonical_boundary=None,
        output_regions=(
            RegionObject(
                region=final_region,
                layer=shape.layer,
                metadata=RegionMetadata(
                    owner_sid=shape.sid,
                    role="via_output",
                    source_sid=source_boundary.metadata.source_sid,
                    point_count_before_region=len(inner.points) + len(outer.points),
                ),
            ),
        ),
    )


def _execute_rings(shape: RingsSpec, by_sid: dict[int, ShapeResult], context: GeometryContext) -> ShapeResult:
    source_boundary = _resolve_shape_source_boundary(shape, by_sid, context)
    output_regions: list[RegionObject] = []
    ring_fillets = shape.fillet.rings if shape.fillet and shape.fillet.rings else None
    for index in range(shape.count):
        ring_fillet = ring_fillets[index] if ring_fillets is not None else None
        inner_offset = index * shape.pitch
        outer_offset = index * shape.pitch + shape.width
        inner = _offset_boundary(source_boundary, inner_offset, shape.layer, context, "ring_inner")
        outer = _offset_boundary(source_boundary, outer_offset, shape.layer, context, "ring_outer")
        inner = apply_fillet(inner, ring_fillet.inner if ring_fillet else None)
        outer = apply_fillet(outer, ring_fillet.outer if ring_fillet else None)
        inner_region = boundary_to_region(inner, shape.layer, context, role="ring_inner")
        outer_region = boundary_to_region(outer, shape.layer, context, role="ring_outer")
        final_region = outer_region.region.dup() - inner_region.region
        if final_region.is_empty():
            raise ConfigError([issue("boolean_empty_region", f"$.shapes[{shape.sid}]", f"ring {index} boolean result is empty.")])
        output_regions.append(
            RegionObject(
                region=final_region,
                layer=shape.layer,
                metadata=RegionMetadata(
                    owner_sid=shape.sid,
                    role="ring_output",
                    source_sid=source_boundary.metadata.source_sid,
                    point_count_before_region=len(inner.points) + len(outer.points),
                ),
            )
        )
    return ShapeResult(
        sid=shape.sid,
        name=shape.name,
        shape_type=shape.type,
        layer=shape.layer,
        canonical_boundary=None,
        output_regions=tuple(output_regions),
    )


def _resolve_shape_source_boundary(shape: BaseShapeSpec | ViaSpec | RingsSpec, by_sid: dict[int, ShapeResult], context: GeometryContext) -> BoundaryObject:
    if shape.source.vertices is not None:
        points = normalize_counterclockwise(tuple(shape.source.vertices))
        _validate_boundary(points, shape.sid)
        return BoundaryObject(
            points=points,
            metadata=BoundaryMetadata(owner_sid=shape.sid, source_sid=None, role="source", coordinate_unit=context.unit),
        )
    return _resolve_ref_boundary(shape, by_sid, context)


def _validate_boundary(points: tuple[Point, ...], sid: int) -> None:
    if len(points) < 3 or abs(signed_area(points)) <= EPSILON:
        raise ConfigError([issue("invalid_boundary", f"$.shapes[{sid}].source.vertices", "boundary must have non-zero area.")])
    if has_consecutive_duplicate_points(points):
        raise ConfigError([issue("invalid_boundary", f"$.shapes[{sid}].source.vertices", "boundary has duplicate consecutive points.")])
    if not is_simple_polygon(points):
        raise ConfigError([issue("invalid_boundary", f"$.shapes[{sid}].source.vertices", "boundary is self-intersecting.")])
