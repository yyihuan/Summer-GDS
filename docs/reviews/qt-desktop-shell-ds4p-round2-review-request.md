# DS4P second-round review request: Qt desktop shell migration

## Communication contract

This request file is the complete handoff. Read repository files directly.
Terminal output is not the deliverable.

Write the complete review only to:

`docs/reviews/qt-desktop-shell-ds4p-round2-review.md`

Do not modify the migration plan, disposition, diagrams, application source,
tests, packaging files, or any other documentation. Do not overwrite the
first-round review.

## Required materials

Read:

1. `docs/planning/qt-desktop-shell-migration-plan.md` (v1.1)
2. `docs/reviews/qt-desktop-shell-round1-disposition.md`
3. `docs/reviews/qt-desktop-shell-ds4p-review.md`
4. `docs/reviews/qt-desktop-shell-glm-review.md`
5. all four `.mmd` sources and matching `.svg` files under `docs/diagrams/`
6. `.graphify/GRAPH_REPORT.md`
7. `.graphify/flows.json`
8. `src/summer_gds/gui/launcher.py`
9. `src/summer_gds/gui/desktop.py`
10. `src/summer_gds/gui/server.py`
11. `src/summer_gds/gui/service.py`
12. `src/summer_gds/gui/static/app.js`
13. `pyproject.toml`
14. `uv.lock`
15. root `SummerGDS.spec`
16. relevant `tests/gui/`

The graph is a code-baseline aid built from commit `dc4d0dd`; the revised plan
and review documents are intentionally uncommitted and must be read directly.
You may use Graphify read-only commands such as `graphify summary`,
`graphify query`, and `graphify flows get`.

## Review objective

Perform an adversarial closure review of plan v1.1, not an implementation
review. Determine whether the revision closes every first-round blocker and
high-risk ambiguity without introducing a new unbounded requirement.

Pay particular attention to:

- PyInstaller built-in hook strategy versus rejected blanket
  `collect_all("PySide6")`, and whether the inventory/real-run gate is
  sufficient.
- KLayout minimal import/dynamic-library strategy and whether the plan
  correctly treats Qt conflict as a risk to exclude rather than an established
  fact.
- `GuiSession.path_tokens` locking, token reuse, purge, preview concurrency,
  and shutdown cleanup.
- dialog single-flight, 100/120-second timeout relation, atomic terminal
  states, gate release, late-result discard, exception response semantics, and
  the deliberate non-reliance on Flask client-disconnect detection.
- `RequestGate`, server shutdown, worker drain, deferred session cleanup,
  QApplication lifetime, and `aboutToQuit` fallback.
- off-the-record profile, JavaScript/DOM diagnostics, renderer crash policy,
  Flask production settings, and security restrictions.
- exact dependency and Windows wheel intersection claims.
- licensing, macOS, Windows ARM x64 emulation, and native Windows x64 evidence
  boundaries.
- whether every requirement is mapped to a concrete phase and executable gate.

Challenge the explicit rejected/modified decisions in the disposition. If one
is unsafe, explain the concrete failure mode; do not merely restate the
first-round preference.

## Output format

The review document must contain:

1. Overall verdict: `APPROVE`, `APPROVE_WITH_CHANGES`, or `BLOCK`.
2. First-round blocker closure matrix, one row per DS4P B1-B4 and H1-H8.
3. New blocking findings, or `None`.
4. Remaining high/medium/low findings, or `None` per category.
5. Review of every modified/rejected decision D01, D04, D06, D07, D10,
   D13-D19.
6. Evidence with repository paths and line references where possible.
7. Exact required text/acceptance changes for each blocking or high finding.
8. Final implementation-readiness checklist.

Do not fail the plan merely because application code has not yet implemented
the plan; implementation starts only after review closure. Do fail it if an
implementation agent could still make two materially different correctness or
release-safety choices.
