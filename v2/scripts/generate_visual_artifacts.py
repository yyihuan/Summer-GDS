from __future__ import annotations

from pathlib import Path

from summer_gds.app.service import ExportOptions, export_artifact, validate_config_file


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "visual"
OUTPUT_DIR = ROOT / "tests" / "_visual_output"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for fixture in sorted(FIXTURE_DIR.glob("*.yaml")):
        case_dir = OUTPUT_DIR / fixture.stem
        case_dir.mkdir(parents=True, exist_ok=True)
        validate_config_file(fixture)
        for format_name in ("png", "svg", "gds"):
            output = case_dir / f"{fixture.stem}.{format_name}"
            result = export_artifact(
                fixture,
                ExportOptions(format=format_name, out=output, force=True),
            )
            print(f"{fixture.stem}: {format_name} -> {result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
