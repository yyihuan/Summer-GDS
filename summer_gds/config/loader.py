"""YAML file loading with no business-level defaults or inference."""

from pathlib import Path

import yaml

from .errors import ConfigIssue, ConfigValidationError


def load_yaml_file(path):
    """Load a YAML file and return raw Python data."""
    yaml_path = Path(path)
    with yaml_path.open("r", encoding="utf-8") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise ConfigValidationError(
                [
                    ConfigIssue(
                        path="$",
                        code="yaml_parse_error",
                        message="YAML could not be parsed: %s" % exc,
                        hint="Fix the YAML syntax before validating Summer-GDS fields.",
                    )
                ]
            )
    return data
