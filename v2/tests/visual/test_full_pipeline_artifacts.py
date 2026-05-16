from pathlib import Path

import pytest

from summer_gds.app.service import ExportOptions, export_artifact, validate_config_file
from summer_gds.schema.errors import ConfigError


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
VISUAL_FIXTURE_DIR = FIXTURE_DIR / "visual"
INVALID_FIXTURE_DIR = FIXTURE_DIR / "invalid"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "_visual_output"


VISUAL_CASES = [
    "base_rectangle_fillet",
    "base_concave_arrow",
    "base_sharp_spike",
    "base_obtuse_wide",
    "base_ref_offset_stack",
    "via_window",
    "rings_three",
    "rings_fillet",
    "rings_array_multi",
    "via_independent_fillet_asymmetric",
    "mixed_full_pipeline",
]


INVALID_CASES = {
    "invalid_hourglass": "invalid_boundary",
    "invalid_collinear_fillet": "fillet_collinear_corner",
    "invalid_via_empty": "boolean_empty_region",
    "invalid_rings_pitch": "invalid_ring_pitch_width",
}


@pytest.mark.parametrize("case_name", VISUAL_CASES)
def test_visual_fixture_exports_png_svg_and_gds(case_name):
    fixture = VISUAL_FIXTURE_DIR / f"{case_name}.yaml"
    case_output = OUTPUT_DIR / case_name
    case_output.mkdir(parents=True, exist_ok=True)

    validate_config_file(fixture)
    png = case_output / f"{case_name}.png"
    svg = case_output / f"{case_name}.svg"
    gds = case_output / f"{case_name}.gds"

    png_result = export_artifact(fixture, ExportOptions(format="png", out=png, force=True))
    svg_result = export_artifact(fixture, ExportOptions(format="svg", out=svg, force=True))
    gds_result = export_artifact(fixture, ExportOptions(format="gds", out=gds, force=True))

    for result in (png_result, svg_result, gds_result):
        assert result.output_path.exists()
        assert result.output_path.stat().st_size > 0

    assert png.read_bytes().startswith(b"\x89PNG")
    assert "<svg" in svg.read_text()
    assert gds.stat().st_size > 100


@pytest.mark.parametrize("case_name, expected_code", INVALID_CASES.items())
def test_invalid_visual_fixtures_fail_with_expected_error(case_name, expected_code):
    fixture = INVALID_FIXTURE_DIR / f"{case_name}.yaml"

    with pytest.raises(ConfigError) as exc_info:
        export_artifact(fixture, ExportOptions(format="png", out=OUTPUT_DIR / f"{case_name}.png", force=True))

    assert expected_code in {issue.code for issue in exc_info.value.issues}
