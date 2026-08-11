# DS4P review request: Qt desktop shell migration

## Communication contract

This request file is the complete task handoff. Do not treat terminal output as
the review deliverable.

Write the complete review to:

`docs/reviews/qt-desktop-shell-ds4p-review.md`

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
8. `SummerGDS.spec`
9. `summer_gds_v1/web_gui/qt_launcher.py`
10. `summer_gds_v1/web_gui/qt_mainwindow.py`
11. `summer_gds_v1/SummerGDS.spec`

You may use `graphify summary`, `graphify query`, `graphify flows get`, and
read-only repository commands if useful.

## Review focus

Perform an adversarial architecture and migration review:

- Validate that the plan solves the observed pywebview/pythonnet compatibility
  problem without claiming broader proof.
- Challenge the Qt/Flask lifecycle, GUI-thread bridge, shutdown ordering,
  WebEngine security boundary, and packaging assumptions.
- Identify hidden Windows, macOS, ARM-emulation, native-library, QtWebEngine,
  installer, and licensing risks.
- Check rollback safety and phase gates.
- Check that GUI/API/YAML/business-core scope is unambiguous.
- Identify missing tests, failure states, observability, or recovery semantics.
- Cross-check plan claims against actual code and the Graphify graph.

## Output format

The review document must contain:

1. Overall verdict: `APPROVE`, `APPROVE_WITH_CHANGES`, or `BLOCK`.
2. Blocking findings.
3. High, medium, and low findings.
4. Evidence with repository file paths and line references where possible.
5. Required plan changes.
6. Optional improvements.
7. A final implementation-readiness checklist.

If no finding exists in a category, write `None`.
