from __future__ import annotations

from pathlib import Path


def atomic_temp_output_path(output_path: Path) -> Path:
    """Return an adjacent temporary name while preserving the writer's suffix."""
    return output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")
