"""Command line interface for the Summer-GDS MVP."""

import argparse
import sys

from mvp_summer_gds.app import generate_config_file, validate_config_file
from mvp_summer_gds.config.errors import ConfigValidationError, GDSWriteError, format_issues


class CliArgumentError(Exception):
    pass


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise CliArgumentError(message)


def build_parser():
    parser = ArgumentParser(prog="summer-gds", description="Summer-GDS MVP CLI")
    subcommands = parser.add_subparsers(dest="command")

    validate_parser = subcommands.add_parser("validate", help="Validate a YAML v1 config")
    validate_parser.add_argument("config", help="Path to config YAML")

    generate_parser = subcommands.add_parser("generate", help="Validate and generate a GDS file")
    generate_parser.add_argument("config", help="Path to config YAML")
    generate_parser.add_argument("--out", dest="output", default=None, help="Output GDS path override")
    return parser


def main(argv=None):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.command == "validate":
            summary = validate_config_file(args.config)
            print("OK: %s" % summary.path)
            print("schema_version: %s" % summary.schema_version)
            print("shapes: %s" % summary.shape_count)
            print("output_file: %s" % summary.output_file)
            return 0
        if args.command == "generate":
            summary = generate_config_file(args.config, args.output)
            print("OK: %s" % summary.output_file)
            print("cell: %s" % summary.cell_name)
            print("shapes_written: %s" % summary.shapes_written)
            print("polygons_written: %s" % summary.polygons_written)
            return 0
        raise CliArgumentError("missing command")
    except CliArgumentError as exc:
        print("ERROR cli_argument", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        print("Use: summer-gds validate <config.yaml> or summer-gds generate <config.yaml> --out <output.gds>", file=sys.stderr)
        return 4
    except FileNotFoundError as exc:
        print("ERROR file_io", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1
    except OSError as exc:
        print("ERROR file_io", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1
    except ConfigValidationError as exc:
        print("ERROR config_invalid", file=sys.stderr)
        print(format_issues(exc.issues), file=sys.stderr)
        return 2
    except GDSWriteError as exc:
        print("ERROR gds_write_failed", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 3
