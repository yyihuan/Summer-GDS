from __future__ import annotations

import math
import re
from numbers import Real
from pathlib import Path
from typing import Any

import yaml

from summer_gds.model.protocol import (
    BaseShapeSpec,
    ConfigSpec,
    GdsSpec,
    GlobalSpec,
    LayerSpec,
    Point,
    RadiusSpec,
    RingFilletSpec,
    RingsFilletSpec,
    RingsSpec,
    SourceSpec,
    ViaFilletSpec,
    ViaOffsets,
    ViaSpec,
)
from summer_gds.schema.errors import ConfigError, ConfigIssue, issue

MAX_YAML_BYTES = 1024 * 1024
MAX_YAML_DEPTH = 32
MAX_RINGS_COUNT = 100


def parse_yaml_text(text: str, base_path: Path) -> ConfigSpec:
    issues: list[ConfigIssue] = []
    if len(text.encode("utf-8")) > MAX_YAML_BYTES:
        raise ConfigError([issue("yaml_too_large", "$", "YAML file exceeds the v2 size limit.")])

    if _contains_yaml_alias_or_anchor(text):
        raise ConfigError([issue("yaml_alias_not_supported", "$", "YAML aliases and anchors are not supported.")])

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError([issue("yaml_parse_error", "$", str(exc))]) from exc

    if not isinstance(raw, dict):
        raise ConfigError([issue("invalid_root", "$", "Top-level YAML value must be a mapping.")])

    if _depth(raw) > MAX_YAML_DEPTH:
        raise ConfigError([issue("yaml_too_deep", "$", "YAML nesting exceeds the v2 depth limit.")])

    _reject_unknown(raw, {"schema_version", "global", "gds", "shapes"}, "$", issues)

    schema_version = _parse_schema_version(raw.get("schema_version"), "$.schema_version", issues)
    global_config = _parse_global(raw.get("global"), "$.global", issues)
    gds = _parse_gds(raw.get("gds"), "$.gds", base_path, issues) if "gds" in raw else None
    shapes = _parse_shapes(raw.get("shapes"), "$.shapes", issues)

    if issues:
        raise ConfigError(issues)
    return ConfigSpec(
        schema_version=schema_version or 2,
        global_config=global_config or GlobalSpec(unit="um", dbu=0.001),
        gds=gds,
        shapes=tuple(shapes),
        base_path=base_path,
    )


def _parse_schema_version(value: Any, path: str, issues: list[ConfigIssue]) -> int | None:
    if not _is_int(value):
        issues.append(issue("invalid_type", path, "schema_version must be integer 2."))
        return None
    if value != 2:
        issues.append(issue("invalid_schema_version", path, "schema_version must be 2."))
        return None
    return value


def _parse_global(value: Any, path: str, issues: list[ConfigIssue]) -> GlobalSpec | None:
    if not isinstance(value, dict):
        issues.append(issue("invalid_type", path, "global must be a mapping."))
        return None
    _reject_unknown(value, {"unit", "dbu", "precision"}, path, issues)

    unit = value.get("unit")
    if unit != "um":
        issues.append(issue("invalid_unit", f"{path}.unit", "global.unit must be um."))

    dbu = _finite_float(value.get("dbu"), f"{path}.dbu", issues)
    if dbu is not None and not 0.00001 <= dbu <= 1.0:
        issues.append(issue("dbu_out_of_range", f"{path}.dbu", "dbu must be between 0.00001 and 1.0 um."))

    precision = None
    if "precision" in value and value.get("precision") is not None:
        precision = _finite_float(value.get("precision"), f"{path}.precision", issues)
        if precision is not None and precision <= 0:
            issues.append(issue("precision_out_of_range", f"{path}.precision", "precision must be positive."))

    if dbu and precision:
        ratio = precision / dbu
        if precision < dbu:
            issues.append(issue("precision_out_of_range", f"{path}.precision", "precision must be >= dbu."))
        elif abs(ratio - round(ratio)) > 1e-10:
            issues.append(issue("precision_dbu_mismatch", f"{path}.precision", "precision must be an integer multiple of dbu."))

    if dbu is None:
        return None
    return GlobalSpec(unit="um", dbu=dbu, precision=precision)


def _parse_gds(value: Any, path: str, base_path: Path, issues: list[ConfigIssue]) -> GdsSpec | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        issues.append(issue("invalid_type", path, "gds must be a mapping."))
        return None
    _reject_unknown(value, {"top_cell", "output"}, path, issues)

    top_cell = value.get("top_cell")
    if top_cell is not None and not isinstance(top_cell, str):
        issues.append(issue("invalid_type", f"{path}.top_cell", "gds.top_cell must be a string."))
        top_cell = None

    output = value.get("output")
    output_path = None
    if output is not None:
        if not isinstance(output, str) or not output:
            issues.append(issue("invalid_output_path", f"{path}.output", "gds.output must be a non-empty string."))
        else:
            output_path = (base_path.parent / output).resolve() if not Path(output).is_absolute() else Path(output)
    return GdsSpec(top_cell=top_cell, output=output_path)


def _parse_shapes(value: Any, path: str, issues: list[ConfigIssue]):
    if not isinstance(value, list) or not value:
        issues.append(issue("invalid_type", path, "shapes must be a non-empty list."))
        return []

    shapes = []
    seen: set[int] = set()
    boundary_capable: set[int] = set()
    for index, item in enumerate(value):
        shape = _parse_shape(item, f"{path}[{index}]", seen, boundary_capable, issues)
        if shape is not None:
            shapes.append(shape)
            seen.add(shape.sid)
            if shape.type == "base_shape":
                boundary_capable.add(shape.sid)
    return shapes


def _parse_shape(value: Any, path: str, seen: set[int], boundary_capable: set[int], issues: list[ConfigIssue]):
    if not isinstance(value, dict):
        issues.append(issue("invalid_type", path, "shape must be a mapping."))
        return None

    shape_type = value.get("type")
    common_keys = {"type", "sid", "name", "layer", "source", "fillet"}
    type_keys = {
        "base_shape": common_keys,
        "via": common_keys | {"offsets"},
        "rings": common_keys | {"count", "pitch", "width"},
    }
    if shape_type not in type_keys:
        issues.append(issue("invalid_type", f"{path}.type", "shape type must be base_shape, via, or rings."))
        allowed = common_keys
    else:
        allowed = type_keys[shape_type]
    _reject_unknown(value, allowed, path, issues)

    sid = _parse_sid(value.get("sid"), f"{path}.sid", seen, issues)
    name = value.get("name")
    if not isinstance(name, str):
        issues.append(issue("invalid_type", f"{path}.name", "name must be a string."))
        name = ""
    layer = _parse_layer(value.get("layer"), f"{path}.layer", issues)
    source = _parse_source(value.get("source"), f"{path}.source", seen, boundary_capable, issues)

    if sid is None or layer is None or source is None or shape_type not in type_keys:
        return None

    if shape_type == "base_shape":
        return BaseShapeSpec(
            type="base_shape",
            sid=sid,
            name=name,
            layer=layer,
            source=source,
            fillet=_parse_radius_spec(value.get("fillet"), f"{path}.fillet", issues),
        )

    if shape_type == "via":
        offsets = _parse_via_offsets(value.get("offsets"), f"{path}.offsets", issues)
        if offsets is None:
            return None
        return ViaSpec(
            type="via",
            sid=sid,
            name=name,
            layer=layer,
            source=source,
            fillet=_parse_via_fillet(value.get("fillet"), f"{path}.fillet", issues),
            offsets=offsets,
        )

    count = _parse_count(value.get("count"), f"{path}.count", issues)
    pitch = _finite_float(value.get("pitch"), f"{path}.pitch", issues)
    width = _finite_float(value.get("width"), f"{path}.width", issues)
    if count is not None and (count <= 0 or count > MAX_RINGS_COUNT):
        issues.append(issue("invalid_rings_count", f"{path}.count", f"rings.count must be 1..{MAX_RINGS_COUNT}."))
    if width is not None and width <= 0:
        issues.append(issue("invalid_ring_pitch_width", f"{path}.width", "rings.width must be positive."))
    if pitch is not None and pitch <= 0:
        issues.append(issue("invalid_ring_pitch_width", f"{path}.pitch", "rings.pitch must be positive."))
    if pitch is not None and width is not None and pitch < width:
        issues.append(issue("invalid_ring_pitch_width", f"{path}.pitch", "rings.pitch must be >= rings.width."))

    fillet = _parse_rings_fillet(value.get("fillet"), f"{path}.fillet", count, issues)
    if count is None or pitch is None or width is None:
        return None
    return RingsSpec(
        type="rings",
        sid=sid,
        name=name,
        layer=layer,
        source=source,
        fillet=fillet,
        count=count,
        pitch=pitch,
        width=width,
    )


def _parse_sid(value: Any, path: str, seen: set[int], issues: list[ConfigIssue]) -> int | None:
    if not _is_int(value):
        issues.append(issue("invalid_type", path, "sid must be an integer."))
        return None
    if value in seen:
        issues.append(issue("duplicate_sid", path, "sid must be globally unique."))
        return None
    return value


def _parse_layer(value: Any, path: str, issues: list[ConfigIssue]) -> LayerSpec | None:
    if not isinstance(value, list) or len(value) != 2 or not all(_is_int(v) and v >= 0 for v in value):
        issues.append(issue("invalid_type", path, "layer must be [layer, datatype] with non-negative integers."))
        return None
    return LayerSpec(layer=value[0], datatype=value[1])


def _parse_source(value: Any, path: str, seen: set[int], boundary_capable: set[int], issues: list[ConfigIssue]) -> SourceSpec | None:
    if not isinstance(value, dict):
        issues.append(issue("invalid_type", path, "source must be a mapping."))
        return None
    _reject_unknown(value, {"vertices", "ref", "offset"}, path, issues)

    has_vertices = "vertices" in value
    has_ref = "ref" in value
    if has_vertices == has_ref:
        issues.append(issue("invalid_source", path, "source must contain exactly one of vertices or ref."))
        return None
    if "offset" in value and not has_ref:
        issues.append(issue("invalid_source", f"{path}.offset", "source.offset is only valid with source.ref."))

    if has_vertices:
        vertices = _parse_vertices(value.get("vertices"), f"{path}.vertices", issues)
        return SourceSpec(vertices=tuple(vertices)) if vertices is not None else None

    ref = value.get("ref")
    if not _is_int(ref):
        issues.append(issue("invalid_type", f"{path}.ref", "source.ref must be an integer."))
        return None
    if ref not in seen:
        issues.append(issue("source_ref_not_found_or_not_ready", f"{path}.ref", "source.ref must point to a previous sid."))
    elif ref not in boundary_capable:
        issues.append(issue("source_ref_not_boundary_capable", f"{path}.ref", "source.ref must point to a base_shape."))

    offset = None
    if "offset" in value:
        offset = _finite_float(value.get("offset"), f"{path}.offset", issues)
    return SourceSpec(ref=ref, offset=offset)


def _parse_vertices(value: Any, path: str, issues: list[ConfigIssue]) -> list[Point] | None:
    if not isinstance(value, list) or len(value) < 3:
        issues.append(issue("invalid_type", path, "vertices must contain at least 3 points."))
        return None
    points: list[Point] = []
    for index, raw_point in enumerate(value):
        point_path = f"{path}[{index}]"
        if not isinstance(raw_point, list) or len(raw_point) != 2:
            issues.append(issue("invalid_type", point_path, "point must be [x, y]."))
            continue
        x = _finite_float(raw_point[0], f"{point_path}[0]", issues)
        y = _finite_float(raw_point[1], f"{point_path}[1]", issues)
        if x is not None and y is not None:
            points.append(Point(x=x, y=y))
    return points if len(points) >= 3 else None


def _parse_via_offsets(value: Any, path: str, issues: list[ConfigIssue]) -> ViaOffsets | None:
    if not isinstance(value, dict):
        issues.append(issue("invalid_type", path, "via.offsets must be a mapping."))
        return None
    _reject_unknown(value, {"inner", "outer"}, path, issues)
    inner = _finite_float(value.get("inner"), f"{path}.inner", issues)
    outer = _finite_float(value.get("outer"), f"{path}.outer", issues)
    if inner is None or outer is None:
        return None
    return ViaOffsets(inner=inner, outer=outer)


def _parse_radius_spec(value: Any, path: str, issues: list[ConfigIssue]) -> RadiusSpec | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        issues.append(issue("invalid_type", path, "fillet must be a mapping."))
        return None
    _reject_unknown(value, {"radius", "radii", "precision"}, path, issues)
    radius = None
    if "radius" in value:
        radius = _finite_float(value.get("radius"), f"{path}.radius", issues)
        if radius is not None and radius < 0:
            issues.append(issue("fillet_radius_out_of_range", f"{path}.radius", "radius must be non-negative."))
    radii = None
    if "radii" in value:
        if not isinstance(value.get("radii"), list):
            issues.append(issue("invalid_type", f"{path}.radii", "radii must be a list."))
        else:
            parsed = []
            for index, raw_radius in enumerate(value["radii"]):
                parsed_radius = _finite_float(raw_radius, f"{path}.radii[{index}]", issues)
                if parsed_radius is not None:
                    parsed.append(parsed_radius)
            radii = tuple(parsed)
    precision = None
    if "precision" in value and value.get("precision") is not None:
        precision = _finite_float(value.get("precision"), f"{path}.precision", issues)
    return RadiusSpec(radius=radius, radii=radii, precision=precision)


def _parse_via_fillet(value: Any, path: str, issues: list[ConfigIssue]) -> ViaFilletSpec | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        issues.append(issue("invalid_type", path, "via.fillet must be a mapping."))
        return None
    _reject_unknown(value, {"inner", "outer"}, path, issues)
    return ViaFilletSpec(
        inner=_parse_radius_spec(value.get("inner"), f"{path}.inner", issues),
        outer=_parse_radius_spec(value.get("outer"), f"{path}.outer", issues),
    )


def _parse_rings_fillet(value: Any, path: str, count: int | None, issues: list[ConfigIssue]) -> RingsFilletSpec | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        issues.append(issue("invalid_type", path, "rings.fillet must be a mapping."))
        return None
    _reject_unknown(value, {"rings"}, path, issues)
    raw_rings = value.get("rings")
    if raw_rings is None:
        return RingsFilletSpec(rings=None)
    if not isinstance(raw_rings, list):
        issues.append(issue("invalid_type", f"{path}.rings", "fillet.rings must be a list."))
        return None
    if count is not None and len(raw_rings) != count:
        issues.append(issue("fillet_rings_length_mismatch", f"{path}.rings", "fillet.rings length must equal rings.count."))
    parsed = []
    for index, raw_ring in enumerate(raw_rings):
        if not isinstance(raw_ring, dict):
            issues.append(issue("invalid_type", f"{path}.rings[{index}]", "ring fillet must be a mapping."))
            continue
        _reject_unknown(raw_ring, {"inner", "outer"}, f"{path}.rings[{index}]", issues)
        parsed.append(
            RingFilletSpec(
                inner=_parse_radius_spec(raw_ring.get("inner"), f"{path}.rings[{index}].inner", issues),
                outer=_parse_radius_spec(raw_ring.get("outer"), f"{path}.rings[{index}].outer", issues),
            )
        )
    return RingsFilletSpec(rings=tuple(parsed))


def _parse_count(value: Any, path: str, issues: list[ConfigIssue]) -> int | None:
    if not _is_int(value):
        issues.append(issue("invalid_rings_count", path, "rings.count must be a positive integer."))
        return None
    return value


def _reject_unknown(value: dict[str, Any], allowed: set[str], path: str, issues: list[ConfigIssue]) -> None:
    for key in value:
        if key not in allowed:
            issues.append(issue("unknown_field", f"{path}.{key}", f"Unknown field: {key}."))


def _finite_float(value: Any, path: str, issues: list[ConfigIssue]) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        issues.append(issue("invalid_type", path, "value must be a finite number."))
        return None
    result = float(value)
    if not math.isfinite(result):
        issues.append(issue("non_finite_number", path, "value must not be NaN or infinity."))
        return None
    return result


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _depth(value: Any) -> int:
    if isinstance(value, dict):
        if not value:
            return 1
        return 1 + max(_depth(item) for item in value.values())
    if isinstance(value, list):
        if not value:
            return 1
        return 1 + max(_depth(item) for item in value)
    return 1


def _contains_yaml_alias_or_anchor(text: str) -> bool:
    return bool(re.search(r"(^|[\s\[{,])([&*])[A-Za-z0-9_-]+", text))
