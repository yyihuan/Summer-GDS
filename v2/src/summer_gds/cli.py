from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from summer_gds.app.service import ExportOptions, export_artifact, validate_config_file
from summer_gds.schema.errors import ConfigError


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            config = validate_config_file(Path(args.config))
            _print_validate_success(config, args.report)
            return 0
        if args.command == "export":
            result = export_artifact(
                Path(args.config),
                ExportOptions(
                    format=args.format,
                    out=Path(args.out) if args.out else None,
                    dry_run=args.dry_run,
                    force=args.force,
                ),
            )
            _print_export_success(result, args.report)
            return 0
        if args.command == "generate":
            result = export_artifact(
                Path(args.config),
                ExportOptions(format="gds", out=Path(args.out) if args.out else None, dry_run=args.dry_run, force=args.force),
            )
            _print_export_success(result, args.report)
            return 0
        if args.command == "preview":
            result = export_artifact(
                Path(args.config),
                ExportOptions(format=args.format, out=Path(args.out) if args.out else None, dry_run=args.dry_run, force=args.force),
            )
            _print_export_success(result, args.report)
            return 0
    except FileNotFoundError as exc:
        _print_plain_error("file_io_error", str(exc), report=getattr(args, "report", "text"))
        return 1
    except ConfigError as exc:
        _print_config_error(exc, report=getattr(args, "report", "text"))
        return _exit_code_for_config_error(exc)
    return 5


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="summer-gds-v2")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("config")
    validate.add_argument("--report", choices=["text", "json"], default="text")

    export = subparsers.add_parser("export")
    export.add_argument("config")
    export.add_argument("--format", choices=["gds", "png", "svg"], required=True)
    export.add_argument("--out")
    export.add_argument("--dry-run", action="store_true")
    export.add_argument("--force", action="store_true")
    export.add_argument("--report", choices=["text", "json"], default="text")

    generate = subparsers.add_parser("generate")
    generate.add_argument("config")
    generate.add_argument("--out")
    generate.add_argument("--dry-run", action="store_true")
    generate.add_argument("--force", action="store_true")
    generate.add_argument("--report", choices=["text", "json"], default="text")

    preview = subparsers.add_parser("preview")
    preview.add_argument("config")
    preview.add_argument("--format", choices=["png", "svg"], default="png")
    preview.add_argument("--out", required=True)
    preview.add_argument("--dry-run", action="store_true")
    preview.add_argument("--force", action="store_true")
    preview.add_argument("--report", choices=["text", "json"], default="text")
    return parser


def _print_validate_success(config, report: str) -> None:
    if report == "json":
        print(json.dumps({"ok": True, "schema_version": config.schema_version, "shapes": len(config.shapes)}, indent=2))
        return
    print(f"OK {config.base_path}")
    print(f"schema_version: {config.schema_version}")
    print(f"shapes: {len(config.shapes)}")


def _print_export_success(result, report: str) -> None:
    if report == "json":
        print(json.dumps(asdict(result) | {"output_path": str(result.output_path), "ok": True}, indent=2))
        return
    prefix = "DRY-RUN" if result.dry_run else "OK"
    print(f"{prefix} {result.output_path}")
    print(f"format: {result.output_format}")
    print(f"regions: {result.region_count}")


def _print_config_error(error: ConfigError, report: str) -> None:
    if report == "json":
        print(
            json.dumps(
                {
                    "ok": False,
                    "errors": [asdict(issue) for issue in error.issues],
                },
                indent=2,
            )
        )
        return
    first = error.issues[0]
    print("ERROR config_invalid", file=sys.stderr)
    print(f"code: {first.code}", file=sys.stderr)
    print(f"path: {first.path}", file=sys.stderr)
    print(f"message: {first.message}", file=sys.stderr)


def _print_plain_error(code: str, message: str, report: str) -> None:
    if report == "json":
        print(json.dumps({"ok": False, "errors": [{"code": code, "path": "$", "message": message}]}, indent=2))
        return
    print(f"ERROR {code}", file=sys.stderr)
    print(message, file=sys.stderr)


def _exit_code_for_config_error(error: ConfigError) -> int:
    codes = {issue.code for issue in error.issues}
    if any(code.startswith(("offset_", "boolean_", "fillet_")) for code in codes):
        return 3
    if any(code.startswith("output_") or code in {"invalid_output_path", "unsupported_output_format", "gds_output_required", "gds_top_cell_required"} for code in codes):
        return 4
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
