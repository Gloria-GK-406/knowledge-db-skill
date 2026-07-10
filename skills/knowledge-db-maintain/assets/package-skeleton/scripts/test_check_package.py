from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.check_package import check_package


class PackageCheckerTests(unittest.TestCase):
    def test_rejects_empty_multi_value_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("source", "info", "knowledge"):
                (root / name).mkdir()
            (root / "source" / "official.md").write_text("source\n", encoding="utf-8")
            (root / "kb-package-schema.json").write_text(
                json.dumps(
                    {
                        "schema": "kb-package-schema@2",
                        "extends": "kb-core@2",
                        "fields": {
                            "capability": {
                                "type": "string",
                                "multiple": True,
                                "description": "Capability identifier.",
                                "filterable": True,
                                "search": {"enabled": True, "weight": 900},
                                "normalization": "upper-case-code",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / "info" / "example.md").write_text(
                """---
schema: kb-entry@2
kind: info
title: Example
status: active
updated: '2026-07-10'
source:
  - source/official.md
metadata:
  capability: []
---

Body.
""",
                encoding="utf-8",
            )

            self.assertEqual(check_package(root), 2)


if __name__ == "__main__":
    unittest.main()
