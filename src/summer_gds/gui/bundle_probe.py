from __future__ import annotations

import json
import os
import re
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from summer_gds.gui.service import DialogFailure, SaveFileDialog


PROBE_ROOT_ENV = "SUMMER_GDS_BUNDLE_PROBE_ROOT"
PROBE_RUN_ID_ENV = "SUMMER_GDS_BUNDLE_PROBE_RUN_ID"
PROBE_TOTAL_TIMEOUT_SECONDS = 180
PROBE_READY_TIMEOUT_SECONDS = 60
MAX_CONTROL_FILE_BYTES = 16 * 1024
_RUN_ID_RE = re.compile(r"^[0-9a-f]{64}$")


class ProbeActivationError(RuntimeError):
    pass


@dataclass(frozen=True)
class BundleProbe:
    root: Path
    run_id: str

    @property
    def session_root(self) -> Path:
        return self._fixed("session-root")

    @property
    def ready_path(self) -> Path:
        return self._fixed(f"ready-{self.run_id}.json")

    @property
    def command_path(self) -> Path:
        return self._fixed(f"command-{self.run_id}.json")

    @property
    def complete_path(self) -> Path:
        return self._fixed(f"complete-{self.run_id}.json")

    def dialog(self) -> SaveFileDialog:
        return ProbeFileDialog(self)

    def publish_ready(self, *, pid: int, origin: str, process_arch: str) -> None:
        self._write_json(
            self.ready_path,
            {
                "schema_version": 1,
                "run_id": self.run_id,
                "pid": pid,
                "origin": origin,
                "frozen": True,
                "process_arch": process_arch,
                "dom_ready": True,
            },
        )

    def read_command(self) -> str | None:
        if not self.command_path.exists():
            return None
        payload = self._read_json(self.command_path)
        if set(payload) != {"schema_version", "run_id", "command"}:
            raise ProbeActivationError("invalid probe command schema")
        if payload != {"schema_version": 1, "run_id": self.run_id, "command": "shutdown"}:
            raise ProbeActivationError("invalid probe command")
        self.command_path.unlink()
        return "shutdown"

    def publish_complete(
        self,
        *,
        pid: int,
        result: str,
        cleanup: dict[str, bool],
        error_stage: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "schema_version": 1,
            "run_id": self.run_id,
            "pid": pid,
            "result": result,
            "cleanup": cleanup,
        }
        if error_stage is not None:
            payload["error_stage"] = error_stage
        self._write_json(self.complete_path, payload)

    def _fixed(self, name: str) -> Path:
        candidate = self.root / name
        if candidate.parent.resolve() != self.root:
            raise ProbeActivationError("probe path escaped root")
        return candidate

    def _read_json(self, path: Path) -> dict[str, Any]:
        _assert_regular_control_file(path)
        if path.stat().st_size > MAX_CONTROL_FILE_BYTES:
            raise ProbeActivationError("probe control file is too large")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ProbeActivationError("probe control file must contain an object")
        if path.parent.resolve() != self.root:
            raise ProbeActivationError("probe control file escaped root")
        return payload

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        temp_path = self._fixed(f".{path.name}.tmp")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(temp_path, flags, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, path)
        finally:
            if temp_path.exists():
                temp_path.unlink()


class ProbeFileDialog:
    def __init__(self, probe: BundleProbe) -> None:
        self._probe = probe

    def choose_open_path(self, kind: str) -> Path | None:
        if kind != "yaml":
            raise DialogFailure("dialog_error", "The bundle probe rejected an unsupported input.")
        return self._probe._fixed("input.yaml")

    def choose_save_path(self, kind: str, suggested_name: str | None) -> Path | None:
        if kind == "yaml":
            return self._probe._fixed("output.yaml")
        if kind == "gds":
            return self._probe._fixed("output.gds")
        raise DialogFailure("dialog_error", "The bundle probe rejected an unsupported output.")


def activate_bundle_probe(environ: dict[str, str] | None = None) -> BundleProbe | None:
    values = os.environ if environ is None else environ
    root_value = values.get(PROBE_ROOT_ENV)
    run_id = values.get(PROBE_RUN_ID_ENV)
    if root_value is None and run_id is None:
        return None
    if root_value is None or run_id is None:
        raise ProbeActivationError("bundle probe variables must be set together")
    if not getattr(sys, "frozen", False):
        raise ProbeActivationError("bundle probe is only available in a frozen application")
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ProbeActivationError("invalid bundle probe run id")

    root = Path(root_value)
    if root.is_symlink() or not root.is_dir():
        raise ProbeActivationError("invalid bundle probe root")
    canonical = root.resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if canonical.parent != temp_root or canonical.name != f"summer-gds-bundle-probe-{run_id}":
        raise ProbeActivationError("bundle probe root is outside the system temporary directory")
    info = canonical.stat()
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise ProbeActivationError("bundle probe root owner is invalid")
    if os.name == "posix" and stat.S_IMODE(info.st_mode) != 0o700:
        raise ProbeActivationError("bundle probe root permissions are invalid")
    return BundleProbe(root=canonical, run_id=run_id)


def _assert_regular_control_file(path: Path) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ProbeActivationError("probe control path is not a regular file")
