from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConfigIssue:
    code: str
    message: str
    path: str
    detail: dict[str, Any] = field(default_factory=dict)


class ConfigError(Exception):
    def __init__(self, issues: list[ConfigIssue]):
        self.issues = issues
        message = "; ".join(f"{issue.code} at {issue.path}" for issue in issues)
        super().__init__(message)


def issue(code: str, path: str, message: str, **detail: Any) -> ConfigIssue:
    return ConfigIssue(code=code, path=path, message=message, detail=detail)
