from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from summer_gds.model.protocol import (
    BaseShapeSpec,
    ConfigSpec,
    RadiusSpec,
    RingFilletSpec,
    RingsFilletSpec,
    RingsSpec,
    ShapeSpec,
    ViaFilletSpec,
    ViaSpec,
)
from summer_gds.schema.errors import ConfigIssue


def issue_to_dict(config_issue: ConfigIssue) -> dict[str, Any]:
    return asdict(config_issue)


def config_to_dict(config: ConfigSpec) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": config.schema_version,
        "global": {
            "unit": config.global_config.unit,
            "dbu": config.global_config.dbu,
        },
        "shapes": [_shape_to_dict(shape) for shape in config.shapes],
    }
    if config.global_config.precision is not None:
        result["global"]["precision"] = config.global_config.precision
    if config.gds is not None:
        gds: dict[str, Any] = {}
        if config.gds.top_cell is not None:
            gds["top_cell"] = config.gds.top_cell
        if config.gds.output is not None:
            gds["output"] = _path_to_string(config.gds.output)
        result["gds"] = gds
    return result


def canonical_yaml(config: ConfigSpec) -> str:
    return yaml.safe_dump(config_to_dict(config), sort_keys=False, allow_unicode=False)


def field_map_for_config(config: ConfigSpec) -> dict[str, str]:
    field_map = {
        "$.schema_version": "schema_version",
        "$.global.unit": "global.unit",
        "$.global.dbu": "global.dbu",
        "$.global.precision": "global.precision",
        "$.gds.top_cell": "gds.top_cell",
        "$.gds.output": "gds.output",
    }
    for index, shape in enumerate(config.shapes):
        prefix = f"$.shapes[{index}]"
        target = f"shape:{shape.sid}"
        field_map[f"{prefix}.type"] = f"{target}.type"
        field_map[f"{prefix}.sid"] = f"{target}.sid"
        field_map[f"{prefix}.name"] = f"{target}.name"
        field_map[f"{prefix}.layer"] = f"{target}.layer"
        field_map[f"{prefix}.source.vertices"] = f"{target}.source.vertices"
        if shape.source.vertices is not None:
            for vertex_index, _point in enumerate(shape.source.vertices):
                field_map[f"{prefix}.source.vertices[{vertex_index}][0]"] = f"{target}.source.vertices.{vertex_index}.x"
                field_map[f"{prefix}.source.vertices[{vertex_index}][1]"] = f"{target}.source.vertices.{vertex_index}.y"
        field_map[f"{prefix}.source.ref"] = f"{target}.source.ref"
        field_map[f"{prefix}.source.offset"] = f"{target}.source.offset"
        field_map[f"{prefix}.fillet"] = f"{target}.fillet"
        if isinstance(shape, ViaSpec):
            field_map[f"{prefix}.offsets.inner"] = f"{target}.offsets.inner"
            field_map[f"{prefix}.offsets.outer"] = f"{target}.offsets.outer"
            field_map[f"{prefix}.fillet.inner"] = f"{target}.fillet.inner"
            field_map[f"{prefix}.fillet.outer"] = f"{target}.fillet.outer"
        if isinstance(shape, RingsSpec):
            field_map[f"{prefix}.count"] = f"{target}.count"
            field_map[f"{prefix}.pitch"] = f"{target}.pitch"
            field_map[f"{prefix}.width"] = f"{target}.width"
            field_map[f"{prefix}.fillet.rings"] = f"{target}.fillet.rings"
    return field_map


def _shape_to_dict(shape: ShapeSpec) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": shape.type,
        "sid": shape.sid,
        "name": shape.name,
        "layer": [shape.layer.layer, shape.layer.datatype],
        "source": _source_to_dict(shape),
    }
    fillet = _fillet_to_dict(shape.fillet)
    if fillet is not None:
        result["fillet"] = fillet
    if isinstance(shape, ViaSpec):
        result["offsets"] = {
            "inner": shape.offsets.inner,
            "outer": shape.offsets.outer,
        }
    if isinstance(shape, RingsSpec):
        result["count"] = shape.count
        result["pitch"] = shape.pitch
        result["width"] = shape.width
    return result


def _source_to_dict(shape: ShapeSpec) -> dict[str, Any]:
    source = shape.source
    if source.vertices is not None:
        return {"vertices": [[point.x, point.y] for point in source.vertices]}
    result: dict[str, Any] = {"ref": source.ref}
    if source.offset is not None:
        result["offset"] = source.offset
    return result


def _fillet_to_dict(fillet: object) -> dict[str, Any] | None:
    if fillet is None:
        return None
    if isinstance(fillet, RadiusSpec):
        return _radius_to_dict(fillet)
    if isinstance(fillet, ViaFilletSpec):
        result: dict[str, Any] = {}
        if fillet.inner is not None:
            result["inner"] = _radius_to_dict(fillet.inner)
        if fillet.outer is not None:
            result["outer"] = _radius_to_dict(fillet.outer)
        return result or None
    if isinstance(fillet, RingsFilletSpec):
        if fillet.rings is None:
            return None
        return {"rings": [_ring_fillet_to_dict(ring) for ring in fillet.rings]}
    return None


def _ring_fillet_to_dict(fillet: RingFilletSpec) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if fillet.inner is not None:
        result["inner"] = _radius_to_dict(fillet.inner)
    if fillet.outer is not None:
        result["outer"] = _radius_to_dict(fillet.outer)
    return result


def _radius_to_dict(radius: RadiusSpec) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if radius.radius is not None:
        result["radius"] = radius.radius
    if radius.radii is not None:
        result["radii"] = list(radius.radii)
    if radius.precision is not None:
        result["precision"] = radius.precision
    return result


def _path_to_string(path: Path) -> str:
    return str(path)
