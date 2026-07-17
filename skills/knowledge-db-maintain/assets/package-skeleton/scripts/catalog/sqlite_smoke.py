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
        if connection.execute("PRAGMA user_version").fetchone()[0] != 3:
            raise RuntimeError("catalog user_version must be 3")
        indexes = {
            str(row[1])
            for row in connection.execute("PRAGMA index_list(field_value_facets)")
        }
        if "field_value_facets_page_idx" not in indexes:
            raise RuntimeError("catalog is missing field_value_facets_page_idx")

        package = connection.execute(
            "SELECT package_name, name, description, revision FROM packages WHERE package_name = ?",
            (package_name,),
        ).fetchone()
        if package is None:
            raise RuntimeError(f"catalog has no package row for {package_name}")
        if not str(package[1]).strip() or not str(package[2]).strip():
            raise RuntimeError("catalog package row must include a name and description")
        if str(package[3]) != source_revision:
            raise RuntimeError(
                f"catalog package revision is {package[3]!r}, expected {source_revision!r}"
            )

        entry_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM entries WHERE package_name = ?",
                (package_name,),
            ).fetchone()[0]
        )
        expected_facets = set(
            connection.execute(
                "SELECT values_table.field_key, values_table.normalized_value, MIN(values_table.display_value), COUNT(DISTINCT values_table.entry_id) "
                "FROM entry_metadata_values AS values_table "
                "JOIN field_definitions AS definitions ON definitions.id = values_table.field_definition_id "
                "WHERE definitions.package_name = ? AND definitions.filterable = 1 "
                "GROUP BY values_table.field_key, values_table.normalized_value",
                (package_name,),
            ).fetchall()
        )
        actual_facets = set(
            connection.execute(
                "SELECT field_key, normalized_value, display_value, entry_count "
                "FROM field_value_facets WHERE package_name = ?",
                (package_name,),
            ).fetchall()
        )
        if actual_facets != expected_facets:
            raise RuntimeError("catalog field_value_facets do not match filterable entry metadata")
        return {
            "packageName": str(package[0]),
            "name": str(package[1]),
            "description": str(package[2]),
            "revision": str(package[3]),
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
