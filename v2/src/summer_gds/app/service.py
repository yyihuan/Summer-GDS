from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from summer_gds.app.pipeline import execute_config
from summer_gds.schema.errors import ConfigError, issue
from summer_gds.schema.yaml_v2 import parse_yaml_text
from summer_gds.writer.gds_writer import write_gds
from summer_gds.writer.image_renderer import ImageOutputConfig, render_image


@dataclass(frozen=True)
class ExportOptions:
    format: Literal["gds", "png", "svg"]
    out: Path | None = None
    dry_run: bool = False
    force: bool = False


@dataclass(frozen=True)
class ExportResult:
    output_format: str
    output_path: Path
    dry_run: bool
    region_count: int


def validate_config_file(path: Path) -> object:
    config_path = Path(path).resolve()
    return parse_yaml_text(config_path.read_text(), base_path=config_path)


def export_artifact(path: Path, options: ExportOptions) -> ExportResult:
    config_path = Path(path).resolve()
    config = validate_config_file(config_path)
    output_path = _resolve_output_path(config_path, config, options)
    _validate_output_path(output_path, options)

    results = execute_config(config)
    regions = tuple(region for result in results for region in result.output_regions)
    if not regions:
        raise ConfigError([issue("output_empty_input", "$.shapes", "No output regions were produced.")])

    if options.dry_run:
        return ExportResult(
            output_format=options.format,
            output_path=output_path,
            dry_run=True,
            region_count=len(regions),
        )

    temp_path = _temp_output_path(output_path)
    try:
        if options.format == "gds":
            top_cell = config.gds.top_cell if config.gds else None
            if not top_cell:
                raise ConfigError([issue("gds_top_cell_required", "$.gds.top_cell", "GDS export requires gds.top_cell.")])
            write_gds(regions, temp_path, top_cell=top_cell, dbu=config.global_config.dbu)
        elif options.format == "png":
            render_image(regions, ImageOutputConfig(path=temp_path, dbu=config.global_config.dbu))
        else:
            raise ConfigError([issue("unsupported_output_format", "$.format", f"Unsupported output format: {options.format}.")])
        temp_path.replace(output_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return ExportResult(
        output_format=options.format,
        output_path=output_path,
        dry_run=False,
        region_count=len(regions),
    )


def _resolve_output_path(config_path: Path, config: object, options: ExportOptions) -> Path:
    if options.format not in {"gds", "png", "svg"}:
        raise ConfigError([issue("unsupported_output_format", "$.format", f"Unsupported output format: {options.format}.")])

    if options.out is not None:
        raw_output = options.out
        return raw_output if raw_output.is_absolute() else config_path.parent / raw_output

    if options.format == "gds":
        if config.gds and config.gds.output:
            return config.gds.output
        raise ConfigError([issue("gds_output_required", "$.gds.output", "GDS export requires --out or gds.output.")])

    raise ConfigError([issue("invalid_output_path", "$.out", f"{options.format} export requires --out.")])


def _validate_output_path(output_path: Path, options: ExportOptions) -> None:
    suffixes = {"gds": ".gds", "png": ".png", "svg": ".svg"}
    expected_suffix = suffixes.get(options.format)
    if expected_suffix is None:
        raise ConfigError([issue("unsupported_output_format", "$.format", f"Unsupported output format: {options.format}.")])
    if output_path.suffix.lower() != expected_suffix:
        raise ConfigError([issue("invalid_output_path", "$.out", f"{options.format} output must end with {expected_suffix}.")])
    if not output_path.parent.exists():
        raise ConfigError([issue("output_parent_missing", "$.out", f"Output parent directory does not exist: {output_path.parent}")])
    if output_path.exists() and not options.force:
        raise ConfigError([issue("output_exists", "$.out", "Output already exists; pass force=True to overwrite.")])


def _temp_output_path(output_path: Path) -> Path:
    return output_path.with_name(f".{output_path.stem}.tmp{output_path.suffix}")
