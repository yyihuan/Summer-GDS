#!/usr/bin/env python3
"""Create a customer-safe source archive from a committed Git revision."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default="HEAD", help="Committed Git revision to archive (default: HEAD)")
    parser.add_argument("--output", type=Path, required=True, help="Destination .tar.gz path")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    revision = _revision(root, args.revision)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "git",
            "archive",
            "--format=tar.gz",
            f"--prefix=Summer-GDS-{revision[:12]}/",
            f"--output={output}",
            revision,
        ],
        cwd=root,
        check=True,
    )
    print(output)
    return 0


def _revision(root: Path, revision: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
