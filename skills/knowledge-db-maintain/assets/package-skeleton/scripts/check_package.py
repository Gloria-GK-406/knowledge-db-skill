"""Validate this package using the same contract as the SQLite producer."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.catalog.build_catalog import CatalogBuildError, _validate_package


def check_package(kb_root: Path) -> int:
    kb_root = kb_root.resolve()
    if not (kb_root / "source").is_dir():
        print(f"missing required source directory: {kb_root / 'source'}", file=sys.stderr)
        return 2
    try:
        _, _, _, _, errors = _validate_package(
            kb_root,
            package_name=kb_root.name,
            revision="validation",
        )
    except CatalogBuildError as error:
        print(str(error), file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"{error['filePath']}: {error['message']}", file=sys.stderr)
        return 2
    print(f"OK: package validation passed for {kb_root}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kb", type=Path, default=Path("."), help="knowledge package root (default: current directory)")
    args = parser.parse_args(argv)
    return check_package(args.kb)


if __name__ == "__main__":
    raise SystemExit(main())
