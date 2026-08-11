from __future__ import annotations

import os
import stat
import sys
import tempfile
from pathlib import Path

import pytest

from summer_gds.gui.bundle_probe import (
    PROBE_ROOT_ENV,
    PROBE_RUN_ID_ENV,
    ProbeActivationError,
    activate_bundle_probe,
)


def test_probe_is_dormant_without_env():
    assert activate_bundle_probe({}) is None


def test_probe_rejects_partial_invalid_or_nonfrozen_activation(monkeypatch):
    run_id = "a" * 64
    with pytest.raises(ProbeActivationError):
        activate_bundle_probe({PROBE_RUN_ID_ENV: run_id})
    with pytest.raises(ProbeActivationError):
        activate_bundle_probe({PROBE_ROOT_ENV: "/tmp/example", PROBE_RUN_ID_ENV: run_id})
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    with pytest.raises(ProbeActivationError):
        activate_bundle_probe({PROBE_ROOT_ENV: "/tmp/example", PROBE_RUN_ID_ENV: "bad"})


def test_probe_fixed_paths_and_command_are_confined(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    run_id = "b" * 64
    root = Path(tempfile.gettempdir()) / f"summer-gds-bundle-probe-{run_id}"
    root.mkdir(mode=0o700)
    os.chmod(root, stat.S_IRWXU)
    try:
        probe = activate_bundle_probe(
            {PROBE_ROOT_ENV: str(root), PROBE_RUN_ID_ENV: run_id}
        )
        assert probe is not None
        canonical = root.resolve()
        assert probe.dialog().choose_open_path("yaml") == canonical / "input.yaml"
        assert probe.dialog().choose_save_path("yaml", None) == canonical / "output.yaml"
        assert probe.dialog().choose_save_path("gds", None) == canonical / "output.gds"
    finally:
        root.rmdir()


def test_probe_rejects_symlink_root(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    run_id = "c" * 64
    target = tmp_path / "target"
    target.mkdir()
    link = Path(tempfile.gettempdir()) / f"summer-gds-bundle-probe-{run_id}"
    link.symlink_to(target, target_is_directory=True)
    try:
        with pytest.raises(ProbeActivationError):
            activate_bundle_probe(
                {PROBE_ROOT_ENV: str(link), PROBE_RUN_ID_ENV: run_id}
            )
    finally:
        link.unlink()
