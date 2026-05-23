from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PyWebviewSaveFileDialog:
    window: Any
    save_dialog_constant: Any | None = None

    def choose_save_path(self, kind: str, suggested_name: str | None) -> Path | None:
        result = self.window.create_file_dialog(
            self._save_dialog_constant(),
            save_filename=suggested_name,
            file_types=_file_types(kind),
        )
        if not result:
            return None
        if isinstance(result, (list, tuple)):
            return Path(result[0]) if result else None
        return Path(result)

    def _save_dialog_constant(self) -> Any:
        if self.save_dialog_constant is not None:
            return self.save_dialog_constant
        import webview

        return webview.SAVE_DIALOG


def _file_types(kind: str) -> tuple[str, ...]:
    if kind == "gds":
        return ("GDSII layout (*.gds)",)
    if kind == "yaml":
        return ("YAML config (*.yaml;*.yml)",)
    return ("All files (*.*)",)
