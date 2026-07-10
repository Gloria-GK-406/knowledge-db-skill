from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
from typing import Any


def smoke_catalog(
    *,
    catalog_path: Path,
    package_name: str,
    source_revision: str,
    required_tables: tuple[str, ...],
) -> dict[str, Any]:
    connection = sqlite3.connect(catalog_path)
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')"
        ).fetchall()
        existing = {str(row[0]) for row in rows}
        missing = [table for table in required_tables if table not in existing]
        if missing:
            raise RuntimeError(f"catalog is missing required table(s): {', '.join(missing)}")

        package = connection.execute(
            "SELECT package_name, revision FROM packages WHERE package_name = ?",
            (package_name,),
        ).fetchone()
        if package is None:
            raise RuntimeError(f"catalog has no package row for {package_name}")
        if str(package[1]) != source_revision:
            raise RuntimeError(
                f"catalog package revision is {package[1]!r}, expected {source_revision!r}"
            )

        entry_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM entries WHERE package_name = ?",
                (package_name,),
            ).fetchone()[0]
        )
        return {
            "packageName": str(package[0]),
            "revision": str(package[1]),
            "entryCount": entry_count,
            "tables": sorted(existing),
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--require-table", action="append", default=[])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    result = smoke_catalog(
        catalog_path=args.catalog,
        package_name=args.package_name,
        source_revision=args.source_revision,
        required_tables=tuple(args.require_table or ["packages", "entries"]),
    )
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out is None:
        print(text, end="")
    else:
        args.out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
