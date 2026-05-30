# Summer GDS v2 Development Plan

## Goal

Build the v2 implementation in this directory without mutating the MVP package.

The implementation follows the refactor docs:

- YAML v2 is the public protocol.
- CLI/app service owns validation, path resolution, and backend selection.
- Geometry is a pipeline from `BoundaryObject` to `RegionObject`.
- GDS writer and image renderer consume only `RegionObject`.
- Tests are written before each implementation phase.

## Phase 1: YAML v2 Parser And Protocol Model

Scope:

- Strict YAML v2 parser in `schema/yaml_v2.py`.
- Protocol dataclasses in `model/protocol.py`.
- Parser safety: safe YAML, top-level mapping, file size, depth, unknown fields.
- Reference validation: `source.ref` points to earlier `base_shape`.
- Numeric validation: finite numbers only, dbu range, precision/dbu, rings bounds.

Tests first:

- Valid base vertices, base ref offset, via, rings, mixed shapes.
- `validate`-equivalent parser does not require `gds.output`.
- Duplicate `sid`, forward ref, missing ref, ref to via/rings.
- Non-finite numbers, bool-as-number, invalid dbu, invalid rings count/pitch/width.
- Unknown fields and forbidden `outputs`/`output.enabled`.

## Phase 2: Geometry Pipeline Core

Scope:

- `BoundaryObject`, `RegionObject`, `ShapeResult`.
- DBU snap in `region_adapter.py` using half-away-from-zero.
- Base shape vertices and `ref + offset`.
- Fillet before Region conversion for base shapes.

Tests first:

- Convex, concave, sharp, obtuse, and collinear polygon inputs.
- Self-intersecting hourglass rejected.
- Offset before fillet order.
- `canonical_boundary` is pre-fillet.
- RegionObject inputs are not mutated.

Circle note:

- Circle is treated as many-sided polygon and does not need fillet.
- Circle support is intentionally deferred from early tests.

## Phase 3: Output Backends And CLI Service

Scope:

- `export_artifact` app service.
- Output path resolver with suffix checks, parent checks, `--force`, atomic write.
- GDS writer and PNG renderer as sibling backends.
- `validate` vs `export --dry-run` semantics.

Tests first:

- `validate` does not require output path.
- `export --format gds --dry-run` requires final GDS path.
- PNG does not read `gds.output`.
- Existing output requires `force=True`.
- Dry-run writes nothing.
- PNG viewport, layer order, and holes are deterministic.

## Phase 4: Via And Rings

Scope:

- Via inner/outer offset, fillet, boolean diff.
- Rings per-ring inner/outer offsets, optional per-ring fillet, no merge.

Tests first:

- Via based on same canonical source.
- Inner bigger than outer fails.
- Rings count controls output region count.
- `fillet.rings` omitted means no fillet.
- `fillet.rings` length mismatch fails.

## Phase 5: CLI Wiring And End-To-End Fixtures

Scope:

- CLI commands: `validate`, `export`, `generate`, `preview`.
- JSON report mode via `--report json`.
- End-to-end fixture set under `v2/tests/fixtures`.

Tests first:

- Exit codes.
- Human-readable and JSON errors.
- GDS smoke if KLayout is available.
- PNG smoke using image library or file-level checks.
