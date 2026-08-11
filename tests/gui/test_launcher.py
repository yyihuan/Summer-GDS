from __future__ import annotations

from summer_gds.gui import launcher


def test_launcher_delegates_to_qt_shell():
    calls = []
    assert launcher.main(lambda: calls.append(True) or 0) == 0
    assert calls == [True]


def test_launcher_propagates_qt_exit_code():
    assert launcher.main(lambda: 7) == 7


def test_launcher_reports_qt_shell_failure(monkeypatch):
    reports = []
    monkeypatch.setattr(launcher, "_report_fatal", reports.append)

    def fail():
        raise RuntimeError("boom")

    assert launcher.main(fail) == 1
    assert "RuntimeError: boom" in reports[0]
