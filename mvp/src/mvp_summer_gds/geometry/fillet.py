"""MVP fillet strategies.

Bevel remains as the placeholder strategy. arc_v2 is the first radius-based
strategy and intentionally starts with convex polygons only.
"""

import math

from mvp_summer_gds.config.errors import ConfigIssue
from mvp_summer_gds.geometry.corners import ArcCornerPlan, CornerKind, build_corner_contexts
from mvp_summer_gds.geometry.primitives import EPSILON, distance, is_convex_polygon
from mvp_summer_gds.model import Point

MAX_ARC_SEGMENTS_PER_CORNER = 512


def validate_bevel_distances(points, distances, path):
    issues = []
    if len(distances) != len(points):
        issues.append(
            ConfigIssue(
                path=path,
                code="fillet_length_mismatch",
                message="bevel distances length must match vertex count.",
                hint="Provide exactly one distance per polygon vertex.",
            )
        )
        return issues

    if not is_convex_polygon(points):
        issues.append(
            ConfigIssue(
                path=path,
                code="bevel_requires_convex_polygon",
                message="MVP bevel fillet only supports convex polygons.",
                hint="Use fillet: null for this shape or simplify it to a convex polygon.",
            )
        )
        return issues

    for index, value in enumerate(distances):
        if value < 0:
            issues.append(
                ConfigIssue(
                    path="%s[%d]" % (path, index),
                    code="negative_bevel_distance",
                    message="bevel distance must be non-negative.",
                    hint="Use 0 to leave a corner unchanged.",
                )
            )

    for index in range(len(points)):
        edge_length = distance(points[index], points[(index + 1) % len(points)])
        start_cut = distances[index]
        end_cut = distances[(index + 1) % len(points)]
        if start_cut + end_cut >= edge_length - EPSILON:
            issues.append(
                ConfigIssue(
                    path=path,
                    code="bevel_distance_too_large",
                    message="bevel distances consume an entire edge at edge %d." % index,
                    hint="Reduce adjacent bevel distances so their sum is smaller than the edge length.",
                )
            )
    return issues


def apply_bevel(points, distances):
    """Apply a straight-line bevel to a convex polygon.

    The schema validator runs the same constraints before this function is
    reached. This function still checks them so direct geometry callers fail
    loudly instead of producing malformed polygons.
    """
    issues = validate_bevel_distances(points, distances, "fillet.distances")
    if issues:
        raise ValueError("; ".join(issue.message for issue in issues))

    output = []
    count = len(points)
    for index, point in enumerate(points):
        cut_distance = distances[index]
        if cut_distance == 0:
            output.append(point)
            continue

        previous_point = points[(index - 1) % count]
        next_point = points[(index + 1) % count]
        output.append(_point_toward(point, previous_point, cut_distance))
        output.append(_point_toward(point, next_point, cut_distance))
    return output


def validate_arc_radii(points, radii, path, user_indices=None):
    issues = []
    if len(radii) != len(points):
        issues.append(
            ConfigIssue(
                path=path,
                code="arc_radii_length_mismatch",
                message="arc_v2 radii length must match vertex count.",
                hint="Provide exactly one radius per polygon vertex.",
            )
        )
        return issues

    contexts = build_corner_contexts(points, radii, user_indices)
    tangent_distances = [0.0] * len(points)

    for context in contexts:
        if context.radius < 0:
            issues.append(
                ConfigIssue(
                    path="%s[%d]" % (path, context.user_index),
                    code="negative_arc_radius",
                    message="arc_v2 radius must be non-negative.",
                    hint="Use 0 to leave a corner unchanged.",
                )
            )
            continue
        if context.corner_kind == CornerKind.CONCAVE:
            issues.append(
                ConfigIssue(
                    path="%s[%d]" % (path, context.user_index),
                    code="arc_v2_requires_convex_polygon",
                    message="arc_v2 currently supports convex polygon corners only.",
                    hint="Use fillet: null, bevel, or wait for the concave arc phase.",
                )
            )
            continue
        if context.radius == 0:
            continue
        if context.corner_kind == CornerKind.COLLINEAR:
            issues.append(
                ConfigIssue(
                    path="%s[%d]" % (path, context.user_index),
                    code="arc_v2_collinear_corner",
                    message="arc_v2 cannot round a collinear corner with positive radius.",
                    hint="Use radius 0 for collinear vertices or remove the redundant point.",
                )
            )
            continue
        tangent_distances[context.normalized_index] = _tangent_distance(context)

    if issues:
        return issues

    for index in range(len(points)):
        edge_length = distance(points[index], points[(index + 1) % len(points)])
        start_cut = tangent_distances[index]
        end_cut = tangent_distances[(index + 1) % len(points)]
        if start_cut + end_cut >= edge_length - EPSILON:
            issues.append(
                ConfigIssue(
                    path=path,
                    code="arc_radius_too_large",
                    message="arc_v2 radii consume an entire edge at edge %d." % index,
                    hint="Reduce adjacent radii so their tangent distances fit on the edge.",
                )
            )
    return issues


def apply_arc_v2(points, radii):
    """Apply arc_v2 to a normalized CCW polygon.

    YAML parsing owns clockwise-to-CCW normalization and radius reordering. This
    geometry layer assumes that contract has already been enforced.
    """
    issues = validate_arc_radii(points, radii, "fillet.radii")
    if issues:
        raise ValueError("; ".join(issue.message for issue in issues))

    output = []
    for plan in build_arc_corner_plans(points, radii):
        output.extend(plan.output_points)
    return output


def build_arc_corner_plans(points, radii, user_indices=None):
    """Build per-corner arc plans for a normalized CCW polygon."""
    plans = []
    for context in build_corner_contexts(points, radii, user_indices):
        if context.radius == 0:
            plans.append(
                ArcCornerPlan(
                    context=context,
                    tangent_start=context.vertex,
                    tangent_end=context.vertex,
                    center=None,
                    sweep_direction=0,
                    segment_count=0,
                    output_points=[context.vertex],
                )
            )
            continue

        tangent_start, tangent_end, center = _arc_geometry(context)
        arc_span = _positive_sweep(tangent_start, tangent_end, center)
        segment_count = _segments_for_arc(context.radius, arc_span)
        plans.append(
            ArcCornerPlan(
                context=context,
                tangent_start=tangent_start,
                tangent_end=tangent_end,
                center=center,
                sweep_direction=1,
                segment_count=segment_count,
                output_points=_arc_points(tangent_start, center, arc_span, segment_count),
            )
        )
    return plans


def _point_toward(origin, target, length):
    segment_length = distance(origin, target)
    if segment_length <= EPSILON:
        raise ValueError("Cannot bevel a zero-length edge.")
    ratio = length / segment_length
    return Point(
        x=origin.x + (target.x - origin.x) * ratio,
        y=origin.y + (target.y - origin.y) * ratio,
    )


def _arc_geometry(context):
    tangent_distance = _tangent_distance(context)
    toward_prev = _unit_vector(context.vertex, context.prev_point)
    toward_next = _unit_vector(context.vertex, context.next_point)
    tangent_start = _point_from_unit(context.vertex, toward_prev, tangent_distance)
    tangent_end = _point_from_unit(context.vertex, toward_next, tangent_distance)
    bisector = _unit_sum(toward_prev, toward_next)
    center_distance = context.radius / math.sin(_interior_angle(context) / 2.0)
    center = _point_from_unit(context.vertex, bisector, center_distance)
    return tangent_start, tangent_end, center


def _tangent_distance(context):
    return context.radius / math.tan(_interior_angle(context) / 2.0)


def _interior_angle(context):
    toward_prev = _unit_vector(context.vertex, context.prev_point)
    toward_next = _unit_vector(context.vertex, context.next_point)
    dot = toward_prev.x * toward_next.x + toward_prev.y * toward_next.y
    dot = max(-1.0, min(1.0, dot))
    return math.acos(dot)


def _unit_vector(origin, target):
    segment_length = distance(origin, target)
    if segment_length <= EPSILON:
        raise ValueError("Cannot fillet a zero-length edge.")
    return Point(
        x=(target.x - origin.x) / segment_length,
        y=(target.y - origin.y) / segment_length,
    )


def _unit_sum(left, right):
    length = math.hypot(left.x + right.x, left.y + right.y)
    if length <= EPSILON:
        raise ValueError("Cannot fillet a 180-degree corner.")
    return Point(x=(left.x + right.x) / length, y=(left.y + right.y) / length)


def _point_from_unit(origin, unit, length):
    return Point(x=origin.x + unit.x * length, y=origin.y + unit.y * length)


def _positive_sweep(start, end, center):
    start_angle = math.atan2(start.y - center.y, start.x - center.x)
    end_angle = math.atan2(end.y - center.y, end.x - center.x)
    sweep = (end_angle - start_angle) % (2.0 * math.pi)
    if sweep <= EPSILON:
        raise ValueError("arc_v2 produced a zero sweep.")
    return sweep


def _segments_for_arc(radius, arc_span):
    sagitta_limit = _sagitta_limit(radius)
    cos_term = 1.0 - sagitta_limit / radius
    cos_term = max(-1.0, min(1.0, cos_term))
    theta_max = 2.0 * math.acos(cos_term)
    if theta_max <= EPSILON:
        return MAX_ARC_SEGMENTS_PER_CORNER
    return min(MAX_ARC_SEGMENTS_PER_CORNER, max(2, int(math.ceil(arc_span / theta_max))))


def _sagitta_limit(radius):
    return 0.001 if radius <= 20.0 else 0.01


def _arc_points(start, center, arc_span, segment_count):
    start_angle = math.atan2(start.y - center.y, start.x - center.x)
    radius = distance(start, center)
    points = []
    for index in range(segment_count + 1):
        angle = start_angle + arc_span * index / segment_count
        points.append(
            Point(
                x=center.x + math.cos(angle) * radius,
                y=center.y + math.sin(angle) * radius,
            )
        )
    return points
