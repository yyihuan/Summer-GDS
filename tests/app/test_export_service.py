from pathlib import Path

import pytest

from summer_gds.app.output_paths import atomic_temp_output_path
from summer_gds.app.service import ExportOptions, export_artifact, validate_config_file
from summer_gds.schema.errors import ConfigError


VALID_BASE = """
schema_version: 2
global:
  unit: um
  dbu: 0.001
gds:
  top_cell: TOP
shapes:
  - type: base_shape
    sid: 0
    name: source
    layer: [1, 0]
    source:
      vertices: [[0, 0], [100, 0], [100, 80], [0, 80]]
"""


def write_config(tmp_path: Path, text: str = VALID_BASE) -> Path:
    path = tmp_path / "case" / "config.yaml"
    path.parent.mkdir()
    path.write_text(text, encoding="utf-8")
    return path


def assert_code(exc_info, code: str):
    assert code in {issue.code for issue in exc_info.value.issues}


def test_validate_config_file_does_not_require_gds_output(tmp_path):
    config_path = write_config(tmp_path, VALID_BASE + "# UTF-8: 中文\n")

    config = validate_config_file(config_path)

    assert config.gds is not None
    assert config.gds.output is None


def test_gds_dry_run_requires_final_gds_output_path(tmp_path):
    config_path = write_config(tmp_path)

    with pytest.raises(ConfigError) as exc_info:
        export_artifact(config_path, ExportOptions(format="gds", dry_run=True))

    assert_code(exc_info, "gds_output_required")


def test_png_dry_run_uses_cli_out_and_writes_nothing(tmp_path):
    config_path = write_config(tmp_path)
    output = Path("preview.png")

    result = export_artifact(config_path, ExportOptions(format="png", out=output, dry_run=True))

    assert result.output_path == config_path.parent / output
    assert result.output_format == "png"
    assert result.dry_run is True
    assert not (config_path.parent / output).exists()


def test_output_path_errors_are_reported_before_writing(tmp_path):
    config_path = write_config(tmp_path)

    with pytest.raises(ConfigError) as suffix_error:
        export_artifact(config_path, ExportOptions(format="png", out=Path("bad.gds"), dry_run=True))
    assert_code(suffix_error, "invalid_output_path")

    with pytest.raises(ConfigError) as parent_error:
        export_artifact(config_path, ExportOptions(format="png", out=Path("missing/preview.png"), dry_run=True))
    assert_code(parent_error, "output_parent_missing")

    existing = config_path.parent / "preview.png"
    existing.write_bytes(b"old")
    with pytest.raises(ConfigError) as exists_error:
        export_artifact(config_path, ExportOptions(format="png", out=existing, dry_run=True))
    assert_code(exists_error, "output_exists")


def test_png_and_gds_exports_write_files(tmp_path):
    config_path = write_config(
        tmp_path,
        VALID_BASE.replace("top_cell: TOP", "top_cell: TOP\n  output: layout.gds"),
    )

    png_result = export_artifact(config_path, ExportOptions(format="png", out=Path("preview.png")))
    gds_result = export_artifact(config_path, ExportOptions(format="gds"))

    assert png_result.output_path.exists()
    assert png_result.output_path.stat().st_size > 0
    assert gds_result.output_path.exists()
    assert gds_result.output_path.stat().st_size > 0


def test_force_allows_overwrite(tmp_path):
    config_path = write_config(tmp_path)
    output = config_path.parent / "preview.png"
    output.write_bytes(b"old")

    result = export_artifact(config_path, ExportOptions(format="png", out=output, force=True))

    assert result.output_path == output
    assert output.stat().st_size > 3


def test_svg_export_uses_image_renderer(tmp_path):
    config_path = write_config(tmp_path)
    output = config_path.parent / "preview.svg"

    result = export_artifact(config_path, ExportOptions(format="svg", out=output))

    assert result.output_path == output
    assert output.exists()
    assert output.read_text(encoding="utf-8").lstrip().startswith("<?xml")


def test_atomic_temp_output_name_is_not_hidden_and_preserves_writer_suffix(tmp_path):
    assert atomic_temp_output_path(tmp_path / "layout.gds").name == "layout.tmp.gds"
    assert atomic_temp_output_path(tmp_path / "preview.svg").name == "preview.tmp.svg"
