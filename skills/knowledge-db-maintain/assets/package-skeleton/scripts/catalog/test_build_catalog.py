from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.catalog.build_catalog import CatalogBuildError, build_catalog


class BuildCatalogTests(unittest.TestCase):
    def test_builds_a_v3_catalog_with_package_identity_and_filter_value_facets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "package"
            out_dir = Path(tmp) / "out"
            (root / "info").mkdir(parents=True)
            (root / "knowledge").mkdir()
            (root / "source").mkdir()
            (root / "source" / "official.md").write_text("Official source\n", encoding="utf-8")
            (root / "kb-package.json").write_text(
                json.dumps(
                    {
                        "schema": "kb-package@1",
                        "name": "Example knowledge base",
                        "description": "A package used to verify catalog generation.",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "kb-package-schema.json").write_text(
                json.dumps(
                    {
                        "schema": "kb-package-schema@2",
                        "extends": "kb-core@2",
                        "fields": {
                            "country": {
                                "type": "string",
                                "multiple": True,
                                "description": "Applicable countries.",
                                "filterable": True,
                                "search": {"enabled": True, "weight": 700},
                                "normalization": "upper-case-code",
                                "aliases": {"JP": ["Japan", "日本"]},
                            }
                        },
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "info" / "example.md").write_text(
                """---
schema: kb-entry@2
kind: info
title: Example
status: active
updated: 2026-07-10
source:
  - source/official.md
metadata:
  country:
    - Japan
    - JP
---

# Example

## Scope

Example scope.

## Facts

Body text.

## Notes

Example notes.
""",
                encoding="utf-8",
            )
            (root / "knowledge" / "derived.md").write_text(
                """---
schema: kb-entry@2
kind: knowledge
title: Derived
status: active
updated: 2026-07-10
depends_on:
  - info/example.md
metadata:
  country:
    - JP
---

# Derived

## Problem and Context

Problem.

## Conclusion

Conclusion.

## Limits

Limits.

## Reasoning

Reasoning.
""",
                encoding="utf-8",
            )

            result = build_catalog(
                kb_root=root,
                package_name="example-package",
                revision="abc123",
                out_dir=out_dir,
            )

            self.assertTrue(result["validation"]["ok"])
            self.assertEqual(result["catalog"]["schema"], "kb-catalog@3")
            connection = sqlite3.connect(out_dir / "catalog.sqlite")
            try:
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')"
                    )
                }
                self.assertTrue(
                    {
                        "packages",
                        "entries",
                        "entry_lines",
                        "info_sources",
                        "knowledge_dependencies",
                        "entries_fts",
                        "package_schema",
                        "field_definitions",
                        "entry_metadata_values",
                        "field_value_facets",
                        "metadata_fts",
                    }.issubset(tables)
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT normalized_value FROM entry_metadata_values ORDER BY entry_id, position"
                    ).fetchall(),
                    [("JAPAN",), ("JP",), ("JP",)],
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM knowledge_dependencies"
                    ).fetchone()[0],
                    1,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT schema_id, extends_id, length(schema_sha256) FROM package_schema"
                    ).fetchone(),
                    ("kb-package-schema@2", "kb-core@2", 64),
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT package_name, name, description, revision FROM packages"
                    ).fetchone(),
                    (
                        "example-package",
                        "Example knowledge base",
                        "A package used to verify catalog generation.",
                        "abc123",
                    ),
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT field_key, normalized_value, display_value, entry_count "
                        "FROM field_value_facets ORDER BY field_key, normalized_value"
                    ).fetchall(),
                    [("country", "JAPAN", "JAPAN", 1), ("country", "JP", "JP", 2)],
                )
            finally:
                connection.close()

    def test_rejects_missing_or_invalid_package_descriptor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "package"
            out_dir = Path(tmp) / "out"
            root.mkdir()
            with self.assertRaisesRegex(CatalogBuildError, "missing package descriptor"):
                build_catalog(
                    kb_root=root,
                    package_name="example-package",
                    revision="abc123",
                    out_dir=out_dir,
                )

            (root / "kb-package.json").write_text(
                json.dumps(
                    {"schema": "kb-package@1", "name": "Example", "description": ""}
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(CatalogBuildError, "description must be a non-empty string"):
                build_catalog(
                    kb_root=root,
                    package_name="example-package",
                    revision="abc123",
                    out_dir=out_dir,
                )

    def test_supports_more_than_ten_values_across_metadata_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "package"
            out_dir = Path(tmp) / "out"
            for name in ("source", "info", "knowledge"):
                (root / name).mkdir(parents=True, exist_ok=True)
            (root / "source" / "official.md").write_text("source\n", encoding="utf-8")
            (root / "kb-package.json").write_text(
                json.dumps(
                    {
                        "schema": "kb-package@1",
                        "name": "Example knowledge base",
                        "description": "A package used to verify catalog generation.",
                    }
                ),
                encoding="utf-8",
            )
            (root / "kb-package-schema.json").write_text(
                json.dumps(
                    {
                        "schema": "kb-package-schema@2",
                        "extends": "kb-core@2",
                        "fields": {
                            "country": {"type": "string", "multiple": True, "description": "Countries", "filterable": True, "search": {"enabled": True, "weight": 700}, "normalization": "upper-case-code"},
                            "tags": {"type": "string", "multiple": True, "description": "Tags", "filterable": True, "search": {"enabled": True, "weight": 620}, "normalization": "keyword"},
                        },
                    }
                ),
                encoding="utf-8",
            )
            countries = "\n".join(f"    - C{index}" for index in range(51))
            (root / "info" / "example.md").write_text(
                f"""---
schema: kb-entry@2
kind: info
title: Many values
status: active
updated: '2026-07-10'
source:
  - source/official.md
metadata:
  country:
{countries}
  tags:
    - priority
---

# Many values

## Scope

Scope.

## Facts

Body.

## Notes

Notes.
""",
                encoding="utf-8",
            )

            result = build_catalog(
                kb_root=root,
                package_name="example-package",
                revision="abc123",
                out_dir=out_dir,
            )

            self.assertTrue(result["validation"]["ok"])
            connection = sqlite3.connect(out_dir / "catalog.sqlite")
            try:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM metadata_fts").fetchone()[0], 52)
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
