from pathlib import Path

from summer_gds.cli import main


CONFIG = """
schema_version: 2
global:
  unit: um
  dbu: 0.001
gds:
  top_cell: TOP
  output: layout.gds
shapes:
  - type: base_shape
    sid: 0
    name: source
    layer: [1, 0]
    source:
      vertices: [[0, 0], [100, 0], [100, 80], [0, 80]]
"""


def write_config(tmp_path: Path, text: str = CONFIG) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return path


def test_cli_validate_success(tmp_path, capsys):
    config = write_config(tmp_path)

    exit_code = main(["validate", str(config)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "OK" in captured.out
    assert "shapes: 1" in captured.out


def test_cli_validate_json_error(tmp_path, capsys):
    config = write_config(tmp_path, CONFIG.replace("sid: 0", "sid: true"))

    exit_code = main(["validate", str(config), "--report", "json"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert '"ok": false' in captured.out
    assert '"invalid_type"' in captured.out


def test_cli_export_png_dry_run_writes_nothing(tmp_path, capsys):
    config = write_config(tmp_path)
    output = tmp_path / "preview.png"

    exit_code = main(["export", str(config), "--format", "png", "--out", str(output), "--dry-run"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "DRY-RUN" in captured.out
    assert not output.exists()


def test_cli_preview_and_generate_shortcuts(tmp_path):
    config = write_config(tmp_path)
    png = tmp_path / "preview.png"
    gds = tmp_path / "layout2.gds"

    preview_code = main(["preview", str(config), "--out", str(png)])
    generate_code = main(["generate", str(config), "--out", str(gds)])

    assert preview_code == 0
    assert generate_code == 0
    assert png.exists()
    assert gds.exists()
