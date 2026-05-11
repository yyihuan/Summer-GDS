from pathlib import Path

from summer_gds.cli import main

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "mvp"


def test_cli_validate_success(capsys):
    code = main(["validate", str(FIXTURES / "valid_polygon.yaml")])
    captured = capsys.readouterr()
    assert code == 0
    assert "OK:" in captured.out
    assert "schema_version: 1" in captured.out


def test_cli_validate_invalid_returns_config_error(capsys):
    code = main(["validate", str(FIXTURES / "invalid_old_polygon.yaml")])
    captured = capsys.readouterr()
    assert code == 2
    assert "ERROR config_invalid" in captured.err
    assert "old_schema_detected" in captured.err


def test_cli_generate_writes_gds(tmp_path, capsys):
    output = tmp_path / "cli_polygon.gds"
    code = main(["generate", str(FIXTURES / "valid_polygon.yaml"), "--out", str(output)])
    captured = capsys.readouterr()
    assert code == 0
    assert output.exists()
    assert "polygons_written: 1" in captured.out


def test_cli_argument_error_returns_4(capsys):
    code = main([])
    captured = capsys.readouterr()
    assert code == 4
    assert "ERROR cli_argument" in captured.err
