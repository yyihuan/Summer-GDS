from __future__ import annotations

import math

from summer_gds.geometry.primitives import EPSILON, cross, distance
from summer_gds.model.geometry import BoundaryMetadata, BoundaryObject
from summer_gds.model.protocol import Point, RadiusSpec
from summer_gds.schema.errors import ConfigError, issue

MAX_ARC_SEGMENTS_PER_CORNER = 512


def apply_fillet(boundary: BoundaryObject, fillet: RadiusSpec | None) -> BoundaryObject:
    if fillet is None:
        return boundary
    radii = _expand_radii(fillet, len(boundary.points))
    if all(radius == 0 for radius in radii):
        return boundary

    issues = []
    tangent_distances = [0.0] * len(boundary.points)
    for index, radius in enumerate(radii):
        prev_point = boundary.points[(index - 1) % len(boundary.points)]
        vertex = boundary.points[index]
        next_point = boundary.points[(index + 1) % len(boundary.points)]
        turn = cross(prev_point, vertex, next_point)
        if radius < 0:
            issues.append(issue("fillet_radius_out_of_range", f"$.shapes[{boundary.metadata.owner_sid}].fillet", "radius must be non-negative."))
            continue
        if radius == 0:
            continue
        if abs(turn) <= EPSILON:
            issues.append(issue("fillet_collinear_corner", f"$.shapes[{boundary.metadata.owner_sid}].fillet", "positive fillet radius cannot be applied to a collinear corner."))
            continue
        tangent_distances[index] = _tangent_distance(prev_point, vertex, next_point, radius)
    if issues:
        raise ConfigError(issues)

    for index in range(len(boundary.points)):
        edge_length = distance(boundary.points[index], boundary.points[(index + 1) % len(boundary.points)])
        if tangent_distances[index] + tangent_distances[(index + 1) % len(boundary.points)] >= edge_length - EPSILON:
            raise ConfigError([issue("fillet_radius_out_of_range", f"$.shapes[{boundary.metadata.owner_sid}].fillet", "fillet radii consume an entire edge.")])

    output: list[Point] = []
    for index, radius in enumerate(radii):
        if radius == 0:
            output.append(boundary.points[index])
            continue
        output.extend(_arc_points_for_corner(boundary.points, index, radius, fillet.precision))

    return BoundaryObject(
        points=tuple(output),
        metadata=BoundaryMetadata(
            owner_sid=boundary.metadata.owner_sid,
            source_sid=boundary.metadata.source_sid,
            role="filleted",
            coordinate_unit=boundary.metadata.coordinate_unit,
        ),
    )


def _expand_radii(fillet: RadiusSpec, count: int) -> tuple[float, ...]:
    if fillet.radius is not None:
        return tuple(float(fillet.radius) for _ in range(count))
    if fillet.radii is not None:
        if len(fillet.radii) != count:
            raise ConfigError([issue("fillet_radii_length_mismatch", "$.shapes", "fillet.radii length must match boundary point count.")])
        return tuple(float(radius) for radius in fillet.radii)
    return tuple(0.0 for _ in range(count))


def _arc_points_for_corner(points: tuple[Point, ...], index: int, radius: float, precision: float | None) -> list[Point]:
    prev_point = points[(index - 1) % len(points)]
    vertex = points[index]
    next_point = points[(index + 1) % len(points)]
    toward_prev = _unit_vector(vertex, prev_point)
    toward_next = _unit_vector(vertex, next_point)
    tangent_distance = _tangent_distance(prev_point, vertex, next_point, radius)
    tangent_start = _point_from_unit(vertex, toward_prev, tangent_distance)
    tangent_end = _point_from_unit(vertex, toward_next, tangent_distance)
    bisector = _unit_sum(toward_prev, toward_next)
    center_distance = radius / math.sin(_interior_angle(prev_point, vertex, next_point) / 2.0)
    center = _point_from_unit(vertex, bisector, center_distance)
    sweep = _minor_sweep(tangent_start, tangent_end, center)
    segment_count = _segments_for_arc(radius, sweep, precision)
    return _arc_points(tangent_start, center, sweep, segment_count)


def _tangent_distance(prev_point: Point, vertex: Point, next_point: Point, radius: float) -> float:
    return radius / math.tan(_interior_angle(prev_point, vertex, next_point) / 2.0)


def _interior_angle(prev_point: Point, vertex: Point, next_point: Point) -> float:
    toward_prev = _unit_vector(vertex, prev_point)
    toward_next = _unit_vector(vertex, next_point)
    dot = toward_prev.x * toward_next.x + toward_prev.y * toward_next.y
    return math.acos(max(-1.0, min(1.0, dot)))


def _unit_vector(origin: Point, target: Point) -> Point:
    segment_length = distance(origin, target)
    if segment_length <= EPSILON:
        raise ConfigError([issue("invalid_boundary", "$.shapes", "zero-length boundary edge.")])
    return Point(x=(target.x - origin.x) / segment_length, y=(target.y - origin.y) / segment_length)


def _unit_sum(left: Point, right: Point) -> Point:
    length = math.hypot(left.x + right.x, left.y + right.y)
    if length <= EPSILON:
        raise ConfigError([issue("fillet_collinear_corner", "$.shapes", "cannot fillet a 180-degree corner.")])
    return Point(x=(left.x + right.x) / length, y=(left.y + right.y) / length)


def _point_from_unit(origin: Point, unit: Point, length: float) -> Point:
    return Point(x=origin.x + unit.x * length, y=origin.y + unit.y * length)


def _minor_sweep(start: Point, end: Point, center: Point) -> float:
    start_angle = math.atan2(start.y - center.y, start.x - center.x)
    end_angle = math.atan2(end.y - center.y, end.x - center.x)
    raw_sweep = end_angle - start_angle
    sweep = math.atan2(math.sin(raw_sweep), math.cos(raw_sweep))
    if abs(sweep) <= EPSILON:
        raise ConfigError([issue("fillet_radius_out_of_range", "$.shapes", "fillet produced a zero sweep.")])
    return sweep


def _segments_for_arc(radius: float, arc_span: float, precision: float | None) -> int:
    sagitta_limit = precision if precision is not None else (0.001 if radius <= 20 else 0.01)
    cos_term = max(-1.0, min(1.0, 1.0 - sagitta_limit / radius))
    theta_max = 2.0 * math.acos(cos_term)
    if theta_max <= EPSILON:
        return MAX_ARC_SEGMENTS_PER_CORNER
    return min(MAX_ARC_SEGMENTS_PER_CORNER, max(2, int(math.ceil(abs(arc_span) / theta_max))))


def _arc_points(start: Point, center: Point, arc_span: float, segment_count: int) -> list[Point]:
    start_angle = math.atan2(start.y - center.y, start.x - center.x)
    radius = distance(start, center)
    return [
        Point(
            x=center.x + math.cos(start_angle + arc_span * step / segment_count) * radius,
            y=center.y + math.sin(start_angle + arc_span * step / segment_count) * radius,
        )
        for step in range(segment_count + 1)
    ]
