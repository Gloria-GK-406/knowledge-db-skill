from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.catalog.build_catalog import build_catalog


class BuildCatalogTests(unittest.TestCase):
    def test_builds_a_v2_catalog_from_a_self_contained_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "package"
            out_dir = Path(tmp) / "out"
            (root / "info").mkdir(parents=True)
            (root / "knowledge").mkdir()
            (root / "source").mkdir()
            (root / "source" / "official.md").write_text("Official source\n", encoding="utf-8")
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
---

# Example

Body text.
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

Conclusion.
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
            self.assertEqual(result["catalog"]["schema"], "kb-catalog@2")
            connection = sqlite3.connect(out_dir / "catalog.sqlite")
            try:
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 2)
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
                        "metadata_fts",
                    }.issubset(tables)
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT normalized_value FROM entry_metadata_values ORDER BY entry_id, position"
                    ).fetchall(),
                    [("JAPAN",), ("JP",)],
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
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
