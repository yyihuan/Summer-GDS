"""Structured errors for YAML and geometry validation."""

from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class ConfigIssue:
    path: str
    code: str
    message: str
    hint: str = ""


class ConfigValidationError(Exception):
    """Raised when the input YAML is syntactically valid but not acceptable."""

    def __init__(self, issues: Iterable[ConfigIssue]):
        self.issues = list(issues)
        message = "; ".join("%s: %s" % (issue.path, issue.message) for issue in self.issues)
        super().__init__(message)


class GDSWriteError(Exception):
    """Raised when normalized geometry cannot be written to GDS."""


def format_issues(issues: Iterable[ConfigIssue]) -> str:
    lines: List[str] = []
    for issue in issues:
        lines.append("- path: %s" % issue.path)
        lines.append("  code: %s" % issue.code)
        lines.append("  message: %s" % issue.message)
        if issue.hint:
            lines.append("  hint: %s" % issue.hint)
    return "\n".join(lines)
