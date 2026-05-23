from __future__ import annotations

import hashlib
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from summer_gds.app.pipeline import execute_config
from summer_gds.gui.presenter import canonical_yaml, config_to_dict, field_map_for_config, issue_to_dict
from summer_gds.schema.errors import ConfigError, ConfigIssue, issue
from summer_gds.schema.yaml_v2 import parse_yaml_text
from summer_gds.writer.gds_writer import write_gds
from summer_gds.writer.image_renderer import ImageOutputConfig, render_image


class SaveFileDialog(Protocol):
    def choose_open_path(self, kind: str) -> Path | None:
        pass

    def choose_save_path(self, kind: str, suggested_name: str | None) -> Path | None:
        pass


class NullSaveFileDialog:
    def choose_open_path(self, kind: str) -> Path | None:
        return None

    def choose_save_path(self, kind: str, suggested_name: str | None) -> Path | None:
        return None


@dataclass(frozen=True)
class PathToken:
    kind: str
    path: Path
    expires_at: float


@dataclass
class GuiSession:
    temp_root: Path | None = None
    retention_seconds: int = 24 * 60 * 60
    path_token_ttl_seconds: int = 30 * 60
    file_dialog: SaveFileDialog = field(default_factory=NullSaveFileDialog)
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    path_tokens: dict[str, PathToken] = field(default_factory=dict)

    def __post_init__(self) -> None:
        root = self.temp_root or Path(tempfile.gettempdir()) / "summer-gds-v2-gui"
        self.temp_root = Path(root)
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self._cleanup_stale_sessions()
        self.session_dir.mkdir(parents=True, exist_ok=True)

    @property
    def session_dir(self) -> Path:
        assert self.temp_root is not None
        return self.temp_root / f"session-{self.session_id}"

    def close(self) -> None:
        shutil.rmtree(self.session_dir, ignore_errors=True)

    def parse(self, yaml_text: str) -> dict[str, Any]:
        try:
            config = parse_yaml_text(yaml_text, base_path=self._virtual_yaml_path())
        except ConfigError as exc:
            return _parse_error_response(exc.issues)
        return {
            "ok": True,
            "parsed_config": config_to_dict(config),
            "canonical_yaml": canonical_yaml(config),
            "field_map": field_map_for_config(config),
            "errors": [],
        }

    def validate(self, yaml_text: str) -> dict[str, Any]:
        try:
            config = parse_yaml_text(yaml_text, base_path=self._virtual_yaml_path())
        except ConfigError as exc:
            return {
                "ok": False,
                "shape_count": 0,
                "errors": [issue_to_dict(config_issue) for config_issue in exc.issues],
            }
        return {"ok": True, "shape_count": len(config.shapes), "errors": []}

    def preview_svg(self, yaml_text: str, request_id: str) -> dict[str, Any]:
        svg_path = self.session_dir / f"preview-{_stable_request_id(request_id)}.svg"
        try:
            config = parse_yaml_text(yaml_text, base_path=self._virtual_yaml_path())
            results = execute_config(config)
            regions = tuple(region for result in results for region in result.output_regions)
            if not regions:
                raise ConfigError([issue("output_empty_input", "$.shapes", "No output regions were produced.")])
            render_image(
                regions,
                ImageOutputConfig(path=svg_path, format="svg", dbu=config.global_config.dbu),
            )
            svg_text = svg_path.read_text()
        except ConfigError as exc:
            return _preview_error_response(exc.issues)
        finally:
            if svg_path.exists():
                svg_path.unlink()
        return {
            "ok": True,
            "svg_text": svg_text,
            "region_count": len(regions),
            "errors": [],
        }

    def choose_save_path(self, kind: str, suggested_name: str | None = None) -> dict[str, Any]:
        if kind not in {"yaml", "gds"}:
            return _simple_error_response("invalid_output_kind", "$.kind", "kind must be yaml or gds.")
        selected = self.file_dialog.choose_save_path(kind, suggested_name)
        if selected is None:
            return {"ok": False, "canceled": True, "errors": []}
        path = Path(selected)
        token = secretsafe_token()
        self.path_tokens[token] = PathToken(
            kind=kind,
            path=path,
            expires_at=time.time() + self.path_token_ttl_seconds,
        )
        return {
            "ok": True,
            "path_token": token,
            "path_label": str(path),
            "exists": path.exists(),
            "errors": [],
        }

    def open_yaml(self) -> dict[str, Any]:
        selected = self.file_dialog.choose_open_path("yaml")
        if selected is None:
            return {"ok": False, "canceled": True, "errors": []}
        path = Path(selected)
        path_error = _validate_read_path(path, "yaml")
        if path_error is not None:
            return path_error
        return {
            "ok": True,
            "yaml_text": path.read_text(),
            "path_label": str(path),
            "errors": [],
        }

    def save_yaml(self, yaml_text: str, path_token: str, force: bool = False) -> dict[str, Any]:
        token = self._resolve_path_token(path_token, "yaml")
        if isinstance(token, dict):
            return token
        path = token.path
        path_error = _validate_write_path(path, "yaml", force)
        if path_error is not None:
            return path_error
        try:
            parse_yaml_text(yaml_text, base_path=self._virtual_yaml_path())
        except ConfigError as exc:
            return _simple_issues_response(exc.issues)
        _atomic_write_text(path, yaml_text)
        return {
            "ok": True,
            "path_label": str(path),
            "errors": [],
        }

    def export_gds(self, yaml_text: str, path_token: str, force: bool = False) -> dict[str, Any]:
        token = self._resolve_path_token(path_token, "gds")
        if isinstance(token, dict):
            return token
        path = token.path
        path_error = _validate_write_path(path, "gds", force)
        if path_error is not None:
            return path_error
        try:
            config = parse_yaml_text(yaml_text, base_path=self._virtual_yaml_path())
            if config.gds is None or not config.gds.top_cell:
                raise ConfigError([issue("gds_top_cell_required", "$.gds.top_cell", "GDS export requires gds.top_cell.")])
            results = execute_config(config)
            regions = tuple(region for result in results for region in result.output_regions)
            if not regions:
                raise ConfigError([issue("output_empty_input", "$.shapes", "No output regions were produced.")])
            temp_path = _temp_output_path(path)
            try:
                write_gds(regions, temp_path, top_cell=config.gds.top_cell, dbu=config.global_config.dbu)
                temp_path.replace(path)
            finally:
                if temp_path.exists():
                    temp_path.unlink()
        except ConfigError as exc:
            return _simple_issues_response(exc.issues)
        return {
            "ok": True,
            "path_label": str(path),
            "region_count": len(regions),
            "errors": [],
        }

    def _virtual_yaml_path(self) -> Path:
        return self.session_dir / "input.yaml"

    def _resolve_path_token(self, token: str, expected_kind: str) -> PathToken | dict[str, Any]:
        self._purge_expired_tokens()
        path_token = self.path_tokens.get(token)
        if path_token is None or path_token.kind != expected_kind:
            return _simple_error_response("invalid_path_token", "$.path_token", "Unknown or mismatched path token.")
        return path_token

    def _purge_expired_tokens(self) -> None:
        now = time.time()
        expired = [token for token, value in self.path_tokens.items() if value.expires_at < now]
        for token in expired:
            del self.path_tokens[token]

    def _cleanup_stale_sessions(self) -> None:
        assert self.temp_root is not None
        cutoff = time.time() - self.retention_seconds
        for child in self.temp_root.iterdir():
            if not child.is_dir() or not child.name.startswith("session-"):
                continue
            try:
                if child.stat().st_mtime < cutoff:
                    shutil.rmtree(child, ignore_errors=True)
            except OSError:
                continue


def protocol_error(code: str, path: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "errors": [issue_to_dict(ConfigIssue(code=code, path=path, message=message))],
    }


def _parse_error_response(issues: list[ConfigIssue]) -> dict[str, Any]:
    return {
        "ok": False,
        "parsed_config": None,
        "canonical_yaml": None,
        "field_map": {},
        "errors": [issue_to_dict(config_issue) for config_issue in issues],
    }


def _preview_error_response(issues: list[ConfigIssue]) -> dict[str, Any]:
    return {
        "ok": False,
        "svg_text": None,
        "region_count": 0,
        "errors": [issue_to_dict(config_issue) for config_issue in issues],
    }


def _stable_request_id(request_id: str) -> str:
    return hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:16]


def secretsafe_token() -> str:
    return uuid.uuid4().hex


def _simple_error_response(code: str, path: str, message: str) -> dict[str, Any]:
    return _simple_issues_response([issue(code, path, message)])


def _simple_issues_response(issues: list[ConfigIssue]) -> dict[str, Any]:
    return {
        "ok": False,
        "errors": [issue_to_dict(config_issue) for config_issue in issues],
    }


def _validate_write_path(path: Path, kind: str, force: bool) -> dict[str, Any] | None:
    suffixes = {
        "yaml": {".yaml", ".yml"},
        "gds": {".gds"},
    }
    if path.suffix.lower() not in suffixes[kind]:
        return _simple_error_response("invalid_output_path", "$.path_token", f"{kind} output suffix is invalid.")
    if not path.parent.exists():
        return _simple_error_response("path_missing", "$.path_token", f"Output parent directory does not exist: {path.parent}")
    if path.exists() and not force:
        return _simple_error_response("export_exists", "$.path_token", "Output already exists.")
    return None


def _validate_read_path(path: Path, kind: str) -> dict[str, Any] | None:
    suffixes = {
        "yaml": {".yaml", ".yml"},
    }
    if path.suffix.lower() not in suffixes[kind]:
        return _simple_error_response("invalid_output_path", "$.path", f"{kind} input suffix is invalid.")
    if not path.exists() or not path.is_file():
        return _simple_error_response("path_missing", "$.path", f"Input file does not exist: {path}")
    return None


def _atomic_write_text(path: Path, text: str) -> None:
    temp_path = _temp_output_path(path)
    try:
        temp_path.write_text(text)
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _temp_output_path(path: Path) -> Path:
    return path.with_name(f".{path.stem}.tmp{path.suffix}")
