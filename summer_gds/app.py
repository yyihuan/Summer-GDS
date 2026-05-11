"""Application use cases for the Summer-GDS MVP."""

from dataclasses import dataclass
from pathlib import Path

from summer_gds.config.loader import load_yaml_file
from summer_gds.config.schema import normalize_config
from summer_gds.gds.writer import write_gds
from summer_gds.geometry.renderer import render_config


@dataclass(frozen=True)
class ValidationSummary:
    path: Path
    schema_version: int
    shape_count: int
    output_file: str


@dataclass(frozen=True)
class GenerationSummary:
    output_file: Path
    cell_name: str
    shapes_written: int
    polygons_written: int


def load_config_file(path):
    return normalize_config(load_yaml_file(path))


def validate_config_file(path):
    config = load_config_file(path)
    return ValidationSummary(
        path=Path(path),
        schema_version=config.schema_version,
        shape_count=len(config.shapes),
        output_file=config.gds.output_file,
    )


def generate_config_file(path, output_override=None):
    config = load_config_file(path)
    polygons = render_config(config)
    output_path = Path(output_override or config.gds.output_file)
    write_gds(
        polygons=polygons,
        cell_name=config.gds.cell_name,
        dbu=config.global_config.dbu,
        output_file=output_path,
    )
    return GenerationSummary(
        output_file=output_path,
        cell_name=config.gds.cell_name,
        shapes_written=len(config.shapes),
        polygons_written=len(polygons),
    )
