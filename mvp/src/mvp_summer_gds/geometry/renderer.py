"""Render normalized shapes into GDS-ready polygons."""

from mvp_summer_gds.config.errors import ConfigIssue, ConfigValidationError
from mvp_summer_gds.geometry.circle import DEFAULT_CIRCLE_SEGMENTS, approximate_circle
from mvp_summer_gds.geometry.fillet import apply_arc_v2, apply_bevel
from mvp_summer_gds.model import ArcFillet, BevelFillet, CircleShape, PolygonShape, RenderedPolygon

MAX_RENDERED_VERTICES_PER_SHAPE = 20000
MAX_RENDERED_VERTICES_TOTAL = 100000


def render_config(config):
    rendered = []
    total_vertices = 0
    for shape in config.shapes:
        polygon = render_shape(shape)
        total_vertices += len(polygon.points)
        if total_vertices > MAX_RENDERED_VERTICES_TOTAL:
            raise ConfigValidationError(
                [
                    ConfigIssue(
                        path="shapes",
                        code="rendered_vertex_limit_exceeded",
                        message="Rendered output exceeds the MVP total vertex limit.",
                        hint="Simplify the input or raise the guardrail with performance tests.",
                    )
                ]
            )
        rendered.append(polygon)
    return rendered


def render_shape(shape):
    if isinstance(shape, PolygonShape):
        points = shape.vertices
        if shape.fillet:
            if isinstance(shape.fillet, BevelFillet):
                points = apply_bevel(points, shape.fillet.distances)
            elif isinstance(shape.fillet, ArcFillet):
                points = apply_arc_v2(points, shape.fillet.radii)
            else:
                raise TypeError("Unsupported fillet: %r" % (shape.fillet,))
        return _bounded_polygon(shape.id, shape.layer, points)
    if isinstance(shape, CircleShape):
        points = approximate_circle(shape.center, shape.radius, DEFAULT_CIRCLE_SEGMENTS)
        return _bounded_polygon(shape.id, shape.layer, points)
    raise TypeError("Unsupported normalized shape: %r" % (shape,))


def _bounded_polygon(shape_id, layer, points):
    if len(points) > MAX_RENDERED_VERTICES_PER_SHAPE:
        raise ConfigValidationError(
            [
                ConfigIssue(
                    path="shapes.%s" % shape_id,
                    code="rendered_shape_vertex_limit_exceeded",
                    message="Rendered shape exceeds the MVP per-shape vertex limit.",
                    hint="Simplify the shape or raise the guardrail with performance tests.",
                )
            ]
        )
    return RenderedPolygon(id=shape_id, layer=layer, points=points)
