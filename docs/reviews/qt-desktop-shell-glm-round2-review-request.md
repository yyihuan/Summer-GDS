# GLM second-round review request: Qt desktop shell migration

## Communication contract

This request file is the complete handoff. Read repository files directly.
Terminal output is not the deliverable.

Write the complete review only to:

`docs/reviews/qt-desktop-shell-glm-round2-review.md`

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

Perform a second implementation-executability review. Compare plan v1.1 and
the disposition against both first-round reviews. The question is whether a
fresh implementation agent can build the migration without inventing
concurrency, lifecycle, packaging, platform, or test semantics.

Trace these flows end to end:

1. launch -> Flask readiness -> WebEngine load -> DOM ready;
2. file request -> single-flight -> Qt async dialog -> response/token;
3. timeout -> queued dialog close -> late result -> gate release;
4. window close -> request/dialog gates -> server/worker drain ->
   session cleanup -> Qt quit;
5. direct imports -> PyInstaller hooks -> bundle inventory -> relocated
   source-independent workflow probe;
6. macOS proof -> Windows ARM x64 emulation proof -> native Windows x64
   release proof.

Check specifically:

- response fields for user cancel versus busy/timeout/error/shutdown;
- ordinary Lock scope, purge timing, token reuse, and no token on late result;
- `RequestGate` enter/leave/closing/drain semantics and shutdown timeout;
- whether fake/offscreen tests and real WebEngine/bundle tests have a clean,
  non-overlapping purpose;
- exact files, dependency groups, import-boundary subprocess tests, spec
  authority, bundle verifier inputs, and KLayout smoke;
- the reasons for rejecting client-disconnect correctness, public headless
  mode, automatic renderer reload, global binary string scans, and default
  `collect_all`.

Do not request application implementation in this review. Identify only plan
ambiguity, contradiction, missing step, or unverifiable acceptance criteria.

## Output format

The review document must contain:

1. Overall verdict: `READY`, `READY_WITH_CHANGES`, or `NOT_READY`.
2. First-round closure matrix for GLM B1-B5, M1-M7, T1-T6, and I1-I6.
3. Remaining blocking ambiguities, or `None`.
4. New contradictions or missing implementation steps, or `None`.
5. Missing/weak tests or gates, or `None`.
6. Evidence with repository paths and line references where possible.
7. Exact wording/acceptance changes for every blocking issue.
8. A final ordered implementation checklist referencing plan phases.

An issue is blocking only if the current text permits materially different
implementations or cannot be verified. Distinguish optional hardening from
requirements needed before Phase 1.
