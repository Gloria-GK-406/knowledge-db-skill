from __future__ import annotations

import json
import io
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from scripts.check_package import check_package


class PackageCheckerTests(unittest.TestCase):
    def make_package(self, root: Path) -> None:
        for name in ("source", "info", "knowledge"):
            (root / name).mkdir()
        (root / "source" / "official.md").write_text("source\n", encoding="utf-8")
        (root / "kb-package-schema.json").write_text(
            json.dumps({"schema": "kb-package-schema@2", "extends": "kb-core@2", "fields": {}}),
            encoding="utf-8",
        )

    def info_entry(self, body: str, title: str = "Example") -> str:
        return f"""---
schema: kb-entry@2
kind: info
title: {title}
status: active
updated: '2026-07-10'
source:
  - source/official.md
metadata: {{}}
---

{body}
"""

    def test_accepts_canonical_bodies_lower_headings_and_fenced_heading_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_package(root)
            (root / "info" / "example.md").write_text(
                self.info_entry(
                    """# Example

## Scope

### Detail

```markdown
## Not a real heading
```

## Facts

Facts.

## Notes

Notes."""
                ),
                encoding="utf-8",
            )
            (root / "knowledge" / "guidance.md").write_text(
                """---
schema: kb-entry@2
kind: knowledge
title: Guidance
status: active
updated: '2026-07-10'
depends_on:
  - info/example.md
metadata: {}
---

# Guidance

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

            with redirect_stdout(io.StringIO()):
                self.assertEqual(check_package(root), 0)

    def test_rejects_noncanonical_title_and_section_structures(self) -> None:
        cases = {
            "title mismatch": "# Different\n\n## Scope\n\n## Facts\n\n## Notes",
            "missing": "# Example\n\n## Scope\n\n## Facts",
            "duplicate": "# Example\n\n## Scope\n\n## Facts\n\n## Facts\n\n## Notes",
            "out of order": "# Example\n\n## Facts\n\n## Scope\n\n## Notes",
            "unexpected": "# Example\n\n## Scope\n\n## Details\n\n## Facts\n\n## Notes",
            "empty h2": "# Example\n\n## Scope\n\n##\n\n## Facts\n\n## Notes",
        }
        for label, body in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.make_package(root)
                (root / "info" / "example.md").write_text(self.info_entry(body), encoding="utf-8")
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    self.assertEqual(check_package(root), 2)
                self.assertIn("canonical", stderr.getvalue())

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
