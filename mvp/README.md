# Summer-GDS MVP

This directory contains the isolated MVP implementation for the refactor.

## Boundary

- Runtime package: `mvp_summer_gds`
- Public CLI: `summer-gds`
- Test root: `mvp/tests`
- Fixtures: `mvp/tests/fixtures`

The MVP code must not depend on legacy modules such as `main.py`, `fillet_gds.py`,
`gds_utils`, or `web_gui`. Legacy code also should not import from this package
until the MVP contract is promoted to the main implementation.

## Development Loop

Use the MVP tests as the first compatibility gate:

```bash
uv run python -m pytest mvp/tests
uv run summer-gds validate mvp/tests/fixtures/valid_polygon.yaml
uv run summer-gds generate mvp/tests/fixtures/valid_polygon.yaml --out /tmp/polygon.gds
uv run summer-gds generate mvp/tests/fixtures/valid_polygon_arc.yaml --out /tmp/arc.gds
```

The visual tests generate PNG snapshots under `mvp/tests/_visual_output/`:

```bash
uv run python -m pytest mvp/tests/visual
```

## Current Scope

- `base_shape` polygon and circle.
- Single arc fillet for polygon, including convex and concave corners.
- Optional `fillet.precision`; omitted precision is selected from radius by policy.
- Strict rejection for legacy `mode: arc_v2`, `mode: bevel`, rings, via, and circle fillet.

Future PRD or technical-spec iterations should first update the YAML fixtures and
tests under this directory, then update the implementation.
