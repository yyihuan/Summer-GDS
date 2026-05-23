from __future__ import annotations

import hashlib
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from summer_gds.app.pipeline import execute_config
from summer_gds.gui.presenter import canonical_yaml, config_to_dict, field_map_for_config, issue_to_dict
from summer_gds.schema.errors import ConfigError, ConfigIssue, issue
from summer_gds.schema.yaml_v2 import parse_yaml_text
from summer_gds.writer.image_renderer import ImageOutputConfig, render_image


@dataclass
class GuiSession:
    temp_root: Path | None = None
    retention_seconds: int = 24 * 60 * 60
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)

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

    def _virtual_yaml_path(self) -> Path:
        return self.session_dir / "input.yaml"

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
