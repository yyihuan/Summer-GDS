# GLM review request: Qt desktop shell migration

## Communication contract

This request file is the complete task handoff. Do not treat terminal output as
the review deliverable.

Write the complete review to:

`docs/reviews/qt-desktop-shell-glm-review.md`

Do not modify:

- `docs/planning/qt-desktop-shell-migration-plan.md`
- application source code
- tests
- packaging files
- any other documentation

## Materials

Read:

1. `docs/planning/qt-desktop-shell-migration-plan.md`
2. `.graphify/GRAPH_REPORT.md`
3. `.graphify/flows.json`
4. `src/summer_gds/gui/launcher.py`
5. `src/summer_gds/gui/desktop.py`
6. `src/summer_gds/gui/server.py`
7. `src/summer_gds/gui/service.py`
8. `tests/gui/`
9. `pyproject.toml`
10. `SummerGDS.spec`
11. `summer_gds_v1/web_gui/qt_launcher.py`
12. `summer_gds_v1/web_gui/qt_mainwindow.py`

You may use `graphify summary`, `graphify query`, `graphify flows get`, and
read-only repository commands if useful.

## Review focus

Perform an implementation-executability review:

- Check that every phase maps to concrete repository files and testable
  outcomes.
- Check API compatibility and dependency direction.
- Analyze the Flask-worker to Qt-GUI-thread dialog bridge for deadlocks,
  cancellation, concurrent requests, exceptions, and shutdown.
- Check whether the proposed file split is practical and avoids circular
  imports.
- Check PyInstaller/QtWebEngine resource collection and source-versus-bundle
  verification gates.
- Check macOS-first and Windows-later sequencing.
- Identify ambiguous requirements an implementation agent could interpret in
  multiple ways.
- Cross-check the migration plan against the Graphify graph and actual tests.

## Output format

The review document must contain:

1. Overall verdict: `READY`, `READY_WITH_CHANGES`, or `NOT_READY`.
2. Blocking ambiguities.
3. Missing implementation steps.
4. Missing or weak tests.
5. Repository/doc inconsistencies.
6. Proposed exact wording or acceptance criteria for required fixes.
7. A final ordered implementation checklist.

If no finding exists in a category, write `None`.
