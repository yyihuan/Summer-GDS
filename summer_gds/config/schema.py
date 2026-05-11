"""Strict YAML v1 schema validation and normalization."""

import re

from summer_gds.geometry.fillet import validate_bevel_distances
from summer_gds.geometry.primitives import (
    EPSILON,
    has_consecutive_duplicate_points,
    has_duplicate_points,
    is_finite_number,
    is_simple_polygon,
    normalize_counterclockwise,
    signed_area,
)
from summer_gds.model import (
    BevelFillet,
    CircleShape,
    GdsConfig,
    GlobalConfig,
    Layer,
    NormalizedConfig,
    Point,
    PolygonShape,
)

from .errors import ConfigIssue, ConfigValidationError

CELL_NAME_RE = re.compile(r"^[A-Za-z0-9_.$-]+$")
MAX_SHAPES = 100
MAX_VERTICES = 10000


def normalize_config(raw):
    issues = []
    if not isinstance(raw, dict):
        raise ConfigValidationError(
            [
                ConfigIssue(
                    path="$",
                    code="invalid_document",
                    message="YAML document must be a mapping.",
                    hint="Use top-level schema_version, global, gds, and shapes keys.",
                )
            ]
        )

    _reject_unknown(raw, {"schema_version", "global", "gds", "shapes"}, "$", issues)

    schema_version = raw.get("schema_version")
    if schema_version is None:
        issues.append(_missing("schema_version"))
    elif not isinstance(schema_version, int) or isinstance(schema_version, bool) or schema_version != 1:
        issues.append(
            ConfigIssue(
                path="schema_version",
                code="unsupported_schema_version",
                message="MVP requires schema_version: 1.",
                hint="Add schema_version: 1 or migrate the config first.",
            )
        )

    global_config = _parse_global(raw.get("global"), issues)
    gds_config = _parse_gds(raw.get("gds"), issues)
    shapes = _parse_shapes(raw.get("shapes"), gds_config.default_layer if gds_config else Layer(1, 0), issues)

    if issues:
        raise ConfigValidationError(issues)

    return NormalizedConfig(
        schema_version=1,
        global_config=global_config,
        gds=gds_config,
        shapes=shapes,
    )


def _parse_global(value, issues):
    path = "global"
    if value is None:
        issues.append(_missing(path))
        return None
    if not isinstance(value, dict):
        issues.append(_invalid_type(path, "object"))
        return None

    _reject_unknown(value, {"dbu", "precision"}, path, issues)
    dbu = value.get("dbu", 0.001)
    precision = value.get("precision")

    dbu_value = _finite_float(dbu, "%s.dbu" % path, issues)
    precision_value = None
    if precision is not None:
        precision_value = _finite_float(precision, "%s.precision" % path, issues)

    if dbu_value is not None and not (0.00001 <= dbu_value <= 1.0):
        issues.append(
            ConfigIssue(
                path="%s.dbu" % path,
                code="dbu_out_of_range",
                message="dbu must be between 0.00001 and 1.0 microns.",
                hint="Use the default dbu: 0.001 unless you have a specific grid requirement.",
            )
        )

    if precision_value is not None and not (0.00001 <= precision_value <= 1.0):
        issues.append(
            ConfigIssue(
                path="%s.precision" % path,
                code="precision_out_of_range",
                message="precision must be null or between 0.00001 and 1.0 microns.",
                hint="Use precision: null for MVP unless grid rounding is required.",
            )
        )

    if dbu_value and precision_value:
        ratio = precision_value / dbu_value
        if abs(ratio - round(ratio)) > 1e-10:
            issues.append(
                ConfigIssue(
                    path="%s.precision" % path,
                    code="precision_dbu_mismatch",
                    message="precision must be an integer multiple of dbu.",
                    hint="Choose precision so precision / dbu is an integer.",
                )
            )

    return GlobalConfig(dbu=dbu_value if dbu_value is not None else 0.001, precision=precision_value)


def _parse_gds(value, issues):
    path = "gds"
    if value is None:
        issues.append(_missing(path))
        return None
    if not isinstance(value, dict):
        issues.append(_invalid_type(path, "object"))
        return None

    _reject_unknown(value, {"output_file", "cell_name", "default_layer"}, path, issues)
    output_file = value.get("output_file")
    cell_name = value.get("cell_name")
    default_layer = _parse_layer(value.get("default_layer", [1, 0]), "%s.default_layer" % path, issues)

    if not isinstance(output_file, str) or not output_file:
        issues.append(_invalid_type("%s.output_file" % path, "non-empty string"))
        output_file = ""
    elif not output_file.endswith(".gds"):
        issues.append(
            ConfigIssue(
                path="%s.output_file" % path,
                code="invalid_output_file",
                message="output_file must end with .gds.",
                hint="Use a file name such as output.gds.",
            )
        )

    if not isinstance(cell_name, str) or not cell_name:
        issues.append(_invalid_type("%s.cell_name" % path, "non-empty string"))
        cell_name = ""
    elif not CELL_NAME_RE.match(cell_name):
        issues.append(
            ConfigIssue(
                path="%s.cell_name" % path,
                code="invalid_cell_name",
                message="cell_name contains unsupported characters.",
                hint="Use only letters, numbers, underscore, dot, dollar, or hyphen.",
            )
        )

    return GdsConfig(output_file=output_file, cell_name=cell_name, default_layer=default_layer)


def _parse_shapes(value, default_layer, issues):
    path = "shapes"
    if value is None:
        issues.append(_missing(path))
        return []
    if not isinstance(value, list):
        issues.append(_invalid_type(path, "list"))
        return []
    if not value:
        issues.append(
            ConfigIssue(
                path=path,
                code="empty_shapes",
                message="shapes must contain at least one shape.",
                hint="Add a base_shape polygon or circle.",
            )
        )
        return []
    if len(value) > MAX_SHAPES:
        issues.append(
            ConfigIssue(
                path=path,
                code="too_many_shapes",
                message="MVP supports at most %d shapes." % MAX_SHAPES,
                hint="Split very large jobs or raise the guardrail after adding performance tests.",
            )
        )

    ids = set()
    shapes = []
    for index, item in enumerate(value):
        shape = _parse_shape(item, "%s[%d]" % (path, index), default_layer, issues)
        if shape is None:
            continue
        if shape.id in ids:
            issues.append(
                ConfigIssue(
                    path="%s[%d].id" % (path, index),
                    code="duplicate_shape_id",
                    message="shape id must be unique.",
                    hint="Use a stable unique id per shape.",
                )
            )
        ids.add(shape.id)
        shapes.append(shape)
    return shapes


def _parse_shape(value, path, default_layer, issues):
    if not isinstance(value, dict):
        issues.append(_invalid_type(path, "object"))
        return None

    old_or_unsupported = _detect_old_or_unsupported_shape(value, path, issues)
    if old_or_unsupported:
        return None

    common_allowed = {"id", "type", "geometry_type", "name", "layer", "fillet"}
    geometry_type = value.get("geometry_type")
    if geometry_type == "polygon":
        allowed = common_allowed | {"vertices"}
    elif geometry_type == "circle":
        allowed = common_allowed | {"center", "radius"}
    else:
        allowed = common_allowed | {"vertices", "center", "radius"}
    _reject_unknown(value, allowed, path, issues)

    if value.get("type") != "base_shape":
        issues.append(
            ConfigIssue(
                path="%s.type" % path,
                code="unsupported_mvp_shape",
                message="MVP only supports type: base_shape.",
                hint="rings and via will be added after the base_shape MVP is stable.",
            )
        )
        return None

    shape_id = value.get("id")
    if not isinstance(shape_id, str) or not shape_id:
        issues.append(_invalid_type("%s.id" % path, "non-empty string"))
        return None

    name = value.get("name", "")
    if not isinstance(name, str):
        issues.append(_invalid_type("%s.name" % path, "string"))
        name = ""

    layer = _parse_layer(value.get("layer", default_layer), "%s.layer" % path, issues)

    if geometry_type == "polygon":
        return _parse_polygon_shape(value, path, shape_id, name, layer, issues)
    if geometry_type == "circle":
        return _parse_circle_shape(value, path, shape_id, name, layer, issues)

    issues.append(
        ConfigIssue(
            path="%s.geometry_type" % path,
            code="unsupported_geometry_type",
            message="MVP supports geometry_type: polygon or circle.",
            hint="Use polygon vertices or circle center/radius.",
        )
    )
    return None


def _parse_polygon_shape(value, path, shape_id, name, layer, issues):
    vertices = _parse_vertices(value.get("vertices"), "%s.vertices" % path, issues)
    if vertices is None:
        return None

    normalized_vertices, reversed_order = normalize_counterclockwise(vertices)
    fillet = _parse_fillet(value.get("fillet"), "%s.fillet" % path, len(vertices), issues)
    if fillet and reversed_order:
        fillet = BevelFillet(distances=list(reversed(fillet.distances)))

    if fillet:
        issues.extend(validate_bevel_distances(normalized_vertices, fillet.distances, "%s.fillet.distances" % path))

    return PolygonShape(id=shape_id, name=name, layer=layer, vertices=normalized_vertices, fillet=fillet)


def _parse_circle_shape(value, path, shape_id, name, layer, issues):
    center = _parse_point(value.get("center"), "%s.center" % path, issues)
    radius = _finite_float(value.get("radius"), "%s.radius" % path, issues)
    fillet = value.get("fillet")
    if fillet is not None:
        issues.append(
            ConfigIssue(
                path="%s.fillet" % path,
                code="circle_fillet_not_supported",
                message="circle shapes do not accept fillet in MVP.",
                hint="Use fillet: null or omit fillet for circle shapes.",
            )
        )
    if radius is not None and radius <= 0:
        issues.append(
            ConfigIssue(
                path="%s.radius" % path,
                code="radius_must_be_positive",
                message="circle radius must be greater than 0.",
                hint="Use a positive radius in microns.",
            )
        )
    if center is None or radius is None:
        return None
    return CircleShape(id=shape_id, name=name, layer=layer, center=center, radius=radius)


def _parse_vertices(value, path, issues):
    if isinstance(value, str):
        issues.append(
            ConfigIssue(
                path=path,
                code="string_vertices_not_supported",
                message="MVP requires vertices as a list of [x, y] pairs.",
                hint='Use vertices: [[0, 0], [100, 0], [100, 80], [0, 80]].',
            )
        )
        return None
    if not isinstance(value, list):
        issues.append(_invalid_type(path, "list[[x, y], ...]"))
        return None
    if len(value) < 3:
        issues.append(
            ConfigIssue(
                path=path,
                code="too_few_vertices",
                message="polygon requires at least 3 vertices.",
                hint="Add enough points to define an area.",
            )
        )
        return None
    if len(value) > MAX_VERTICES:
        issues.append(
            ConfigIssue(
                path=path,
                code="too_many_vertices",
                message="MVP supports at most %d vertices per polygon." % MAX_VERTICES,
                hint="Simplify the polygon or raise the guardrail after performance tests.",
            )
        )
        return None

    points = []
    for index, raw_point in enumerate(value):
        point = _parse_point(raw_point, "%s[%d]" % (path, index), issues)
        if point is not None:
            points.append(point)
    if len(points) != len(value):
        return None

    if has_consecutive_duplicate_points(points):
        issues.append(
            ConfigIssue(
                path=path,
                code="consecutive_duplicate_vertices",
                message="polygon contains duplicate neighboring vertices.",
                hint="Remove duplicate points before generating GDS.",
            )
        )
    elif has_duplicate_points(points):
        issues.append(
            ConfigIssue(
                path=path,
                code="duplicate_vertices",
                message="polygon contains duplicate vertices.",
                hint="Each polygon corner should appear once; do not repeat the first point at the end.",
            )
        )
    if not is_simple_polygon(points):
        issues.append(
            ConfigIssue(
                path=path,
                code="self_intersecting_polygon",
                message="polygon edges intersect.",
                hint="Provide a simple polygon without crossing edges.",
            )
        )
    if abs(signed_area(points)) <= EPSILON:
        issues.append(
            ConfigIssue(
                path=path,
                code="zero_area_polygon",
                message="polygon area is zero.",
                hint="Use non-collinear points that enclose an area.",
            )
        )
    return points


def _parse_fillet(value, path, vertex_count, issues):
    if value is None:
        return None
    if not isinstance(value, dict):
        issues.append(_invalid_type(path, "object or null"))
        return None
    if "type" in value:
        issues.append(
            ConfigIssue(
                path="%s.type" % path,
                code="old_fillet_schema",
                message="Old fillet.type schema is not accepted in MVP.",
                hint='Use fillet: null or fillet: {mode: "bevel", distances: [...]}.',
            )
        )
        return None
    if "radii" in value:
        issues.append(
            ConfigIssue(
                path="%s.radii" % path,
                code="old_fillet_schema",
                message="fillet.radii is not accepted in MVP.",
                hint='Use fillet: {mode: "bevel", distances: [...]} for the placeholder fillet.',
            )
        )
        return None

    _reject_unknown(value, {"mode", "distances"}, path, issues)
    mode = value.get("mode")
    if mode != "bevel":
        issues.append(
            ConfigIssue(
                path="%s.mode" % path,
                code="unsupported_fillet_mode",
                message='MVP only supports fillet.mode = "bevel".',
                hint="Use fillet: null or fillet.mode: bevel.",
            )
        )
        return None

    distances = value.get("distances")
    if not isinstance(distances, list):
        issues.append(_invalid_type("%s.distances" % path, "list[float]"))
        return None
    parsed = []
    for index, raw_distance in enumerate(distances):
        parsed_distance = _finite_float(raw_distance, "%s.distances[%d]" % (path, index), issues)
        if parsed_distance is not None:
            parsed.append(parsed_distance)
    if len(parsed) != len(distances):
        return None
    if len(parsed) != vertex_count:
        issues.append(
            ConfigIssue(
                path="%s.distances" % path,
                code="fillet_length_mismatch",
                message="bevel distances length must match vertex count.",
                hint="Provide exactly one distance per polygon vertex.",
            )
        )
        return None
    return BevelFillet(distances=parsed)


def _parse_point(value, path, issues):
    if not isinstance(value, list) or len(value) != 2:
        issues.append(_invalid_type(path, "[x, y]"))
        return None
    x = _finite_float(value[0], "%s[0]" % path, issues)
    y = _finite_float(value[1], "%s[1]" % path, issues)
    if x is None or y is None:
        return None
    return Point(x, y)


def _parse_layer(value, path, issues):
    if isinstance(value, Layer):
        return value
    if not isinstance(value, list) or len(value) != 2:
        issues.append(_invalid_type(path, "[layer, datatype]"))
        return Layer(1, 0)
    layer = _int_in_range(value[0], "%s[0]" % path, issues)
    datatype = _int_in_range(value[1], "%s[1]" % path, issues)
    return Layer(layer if layer is not None else 1, datatype if datatype is not None else 0)


def _detect_old_or_unsupported_shape(value, path, issues):
    has_issue = False
    shape_type = value.get("type")
    if shape_type == "polygon":
        issues.append(
            ConfigIssue(
                path="%s.type" % path,
                code="old_schema_detected",
                message="Old type: polygon schema is not accepted by MVP.",
                hint='Use type: base_shape with geometry_type: polygon.',
            )
        )
        has_issue = True
    elif shape_type in {"rings", "via"}:
        issues.append(
            ConfigIssue(
                path="%s.type" % path,
                code="unsupported_mvp_shape",
                message="MVP only supports base_shape.",
                hint="Implement rings/via after the base_shape MVP is stable.",
            )
        )
        has_issue = True
    for key in ("ring_num", "ring_width", "ring_space", "ring_count", "ring_widths", "ring_spaces"):
        if key in value:
            issues.append(
                ConfigIssue(
                    path="%s.%s" % (path, key),
                    code="unsupported_mvp_shape",
                    message="%s is not supported in MVP." % key,
                    hint="Remove rings-specific fields from MVP configs.",
                )
            )
            has_issue = True
    if "vertices_gen" in value:
        issues.append(
            ConfigIssue(
                path="%s.vertices_gen" % path,
                code="unsupported_generator",
                message="vertices_gen is not supported in MVP.",
                hint="Provide explicit vertices as a list of [x, y] pairs.",
            )
        )
        has_issue = True
    fillet = value.get("fillet")
    if isinstance(fillet, dict) and "type" in fillet:
        issues.append(
            ConfigIssue(
                path="%s.fillet.type" % path,
                code="old_fillet_schema",
                message="Old fillet.type schema is not accepted in MVP.",
                hint='Use fillet: null or fillet.mode: bevel.',
            )
        )
        has_issue = True
    return has_issue


def _reject_unknown(mapping, allowed, path, issues):
    for key in sorted(mapping.keys()):
        if key not in allowed:
            issues.append(
                ConfigIssue(
                    path="%s.%s" % (path, key) if path != "$" else key,
                    code="unknown_field",
                    message="Unknown field %s." % key,
                    hint="Remove the field or add it to the schema before using it.",
                )
            )


def _missing(path):
    return ConfigIssue(
        path=path,
        code="missing_required_field",
        message="Missing required field.",
        hint="Add this field to the YAML config.",
    )


def _invalid_type(path, expected):
    return ConfigIssue(
        path=path,
        code="invalid_type",
        message="Expected %s." % expected,
        hint="Use the canonical YAML v1 type for this field.",
    )


def _finite_float(value, path, issues):
    if not is_finite_number(value):
        issues.append(
            ConfigIssue(
                path=path,
                code="invalid_number",
                message="Expected a finite number.",
                hint="Do not use NaN, inf, booleans, or strings for numeric fields.",
            )
        )
        return None
    return float(value)


def _int_in_range(value, path, issues):
    if isinstance(value, bool) or not isinstance(value, int):
        issues.append(_invalid_type(path, "integer"))
        return None
    if value < 0 or value > 255:
        issues.append(
            ConfigIssue(
                path=path,
                code="layer_out_of_range",
                message="layer and datatype must be between 0 and 255.",
                hint="Use standard GDS layer/datatype integer values.",
            )
        )
        return None
    return value
