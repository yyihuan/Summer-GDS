from pathlib import Path

from summer_gds.app.pipeline import execute_config
from summer_gds.schema.yaml_v2 import parse_yaml_text
from summer_gds.writer.gds_writer import write_gds
from summer_gds.writer.image_renderer import ImageOutputConfig, render_image


def test_image_renderer_is_deterministic_and_does_not_mutate_regions(tmp_path):
    config = parse_yaml_text(
        """
schema_version: 2
global: { unit: um, dbu: 0.001 }
shapes:
  - type: base_shape
    sid: 0
    name: source
    layer: [2, 0]
    source:
      vertices: [[0, 0], [20, 0], [20, 10], [0, 10]]
  - type: base_shape
    sid: 1
    name: source2
    layer: [1, 0]
    source:
      vertices: [[30, 0], [40, 0], [40, 10], [30, 10]]
""",
        base_path=Path("/work/config.yaml"),
    )
    regions = tuple(region for result in execute_config(config) for region in result.output_regions)
    before = [region.region.bbox().to_s() for region in regions]
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"

    render_image(regions, ImageOutputConfig(path=first, width_px=256, height_px=128))
    render_image(regions, ImageOutputConfig(path=second, width_px=256, height_px=128))

    assert first.read_bytes() == second.read_bytes()
    assert [region.region.bbox().to_s() for region in regions] == before


def test_gds_writer_explicitly_selects_gds2_for_atomic_temp_paths(tmp_path):
    config = parse_yaml_text(
        """
schema_version: 2
global: { unit: um, dbu: 0.001 }
shapes:
  - type: base_shape
    sid: 0
    name: source
    layer: [1, 0]
    source:
      vertices: [[0, 0], [20, 0], [20, 10], [0, 10]]
""",
        base_path=tmp_path / "config.yaml",
    )
    regions = tuple(region for result in execute_config(config) for region in result.output_regions)
    output = tmp_path / "layout.atomic-temp"

    write_gds(regions, output, top_cell="TOP", dbu=config.global_config.dbu)

    assert output.exists()
    assert output.stat().st_size > 0
