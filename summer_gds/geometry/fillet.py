"""MVP fillet strategies.

Only bevel is implemented. Arc and adaptive fillets are intentionally rejected
by schema validation until the fab-approved precision model exists.
"""

from summer_gds.config.errors import ConfigIssue
from summer_gds.geometry.primitives import EPSILON, distance, is_convex_polygon


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
