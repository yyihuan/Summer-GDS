# Visual Full-Pipeline Fixtures

These fixtures exercise the full v2 flow:

```text
YAML -> parser -> pipeline -> RegionObject -> PNG/SVG/GDS backend
```

Run:

```bash
PYTHONPATH=v2/src .venv-arm64/bin/python -m pytest v2/tests/visual/test_full_pipeline_artifacts.py -q
```

Generated artifacts are written to:

```text
v2/tests/_visual_output/<case>/
```

Cases:

| Case | Covers |
| --- | --- |
| `base_rectangle_fillet` | Convex rectangle with normal fillet. |
| `base_concave_arrow` | Concave polygon with fillet. |
| `base_sharp_spike` | Very sharp corner with small fillet. |
| `base_obtuse_wide` | Obtuse and wide-angle polygon. |
| `base_ref_offset_stack` | Base plus positive and negative `source.ref + offset`. |
| `via_window` | Via inner/outer offset, fillet, boolean diff. |
| `rings_three` | Three unfilleted rings, no merge. |
| `rings_fillet` | Per-ring inner/outer fillet. |
| `mixed_full_pipeline` | Base, offset base, via, and rings in one file. |

Invalid fixtures live in `../invalid` and cover:

- self-intersecting hourglass topology
- positive fillet on collinear points
- empty via boolean result
- invalid ring pitch/width
