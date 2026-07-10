import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "skills" / "knowledge-db-maintain" / "scripts" / "kb.py"
FIXTURE = ROOT / "tests" / "fixtures" / "metadata-schema-v2"


SCHEMA = {
    "schema": "kb-package-schema@2",
    "extends": "kb-core@2",
    "fields": {
        "tags": {
            "type": "string", "multiple": True, "description": "Lightweight labels",
            "filterable": True, "search": {"enabled": True, "weight": 620},
        },
        "country": {
            "type": "string", "multiple": True, "description": "Applicable country",
            "filterable": True, "search": {"enabled": True, "weight": 700},
            "aliases": {"JP": ["Japan", "日本"]},
        },
        "capability": {
            "type": "string", "multiple": True, "description": "Scope item",
            "filterable": True, "search": {"enabled": True, "weight": 900},
        },
        "release": {
            "type": "string", "description": "Release", "filterable": True,
            "search": {"enabled": False, "weight": 0},
        },
        "note": {
            "type": "string", "description": "Non-queryable note", "filterable": False,
            "search": {"enabled": False, "weight": 0},
        },
    },
}


def entry(kind, title, metadata=None, source=None, depends_on=None, status="active"):
    core = ["schema: kb-core@2", f"kind: {kind}", f"title: {title}", f"status: {status}", "updated: 2026-07-10"]
    if source is not None:
        core += ["source:"] + [f"  - {value}" for value in source]
    if depends_on is not None:
        core += ["depends_on:"] + [f"  - {value}" for value in depends_on]
    if metadata is not None:
        core.append("metadata:")
        for key, value in metadata.items():
            if isinstance(value, list):
                core.append(f"  {key}:")
                core += [f"    - {item}" for item in value]
            else:
                core.append(f"  {key}: {value}")
    return "---\n" + "\n".join(core) + "\n---\n\n# " + title + "\n\nBody text.\n"


class KbCliV2Tests(unittest.TestCase):
    def run_kb(self, root, *args, check=True):
        result = subprocess.run(
            [sys.executable, str(KB), "--kb", str(root), *args],
            capture_output=True, text=True, encoding="utf-8", errors="strict",
        )
        if check and result.returncode:
            self.fail(f"kb {' '.join(args)} returned {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result

    def make_package(self, root):
        for name in ("source", "info", "knowledge"):
            (root / name).mkdir()
        (root / "kb-package-schema.json").write_text(json.dumps(SCHEMA), encoding="utf-8")
        (root / "source" / "official.md").write_text("official", encoding="utf-8")

    def write(self, root, rel, content):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_scan_accepts_declared_nested_metadata_and_required_core_roles(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            self.write(root, "info/sap/16T.md", entry("info", "Intercompany Processing", {"country": ["JP", "DE"], "capability": ["16T"], "tags": ["finance"], "release": '"2602"'}, ["source/official.md"]))
            self.write(root, "knowledge/sap/16T.md", entry("knowledge", "16T conclusion", {"country": ["JP"], "capability": ["16T"]}, depends_on=["info/sap/16T.md"]))
            self.assertIn("OK", self.run_kb(root, "scan").stdout)

    def test_scan_rejects_unknown_metadata_wrong_cardinality_and_missing_core_role(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            self.write(root, "info/bad.md", entry("info", "Bad", {"country": "JP", "unknown": "x"}))
            result = self.run_kb(root, "scan", check=False)
            self.assertEqual(1, result.returncode)
            self.assertIn("undeclared metadata field: unknown", result.stdout)
            self.assertIn("metadata.country must be an array", result.stdout)
            self.assertIn("missing source", result.stdout)

    def test_scan_rejects_package_values_outside_nested_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            content = entry("info", "Bad top level", {"country": ["JP"]}, ["source/official.md"])
            content = content.replace("metadata:\n", "country: JP\nmetadata:\n")
            self.write(root, "info/bad-top-level.md", content)
            result = self.run_kb(root, "scan", check=False)
            self.assertEqual(1, result.returncode)
            self.assertIn("unexpected frontmatter field: country", result.stdout)

    def test_schema_lists_merged_core_and_package_fields_in_human_and_json_forms(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            human = self.run_kb(root, "schema").stdout
            self.assertIn("title (core)", human); self.assertIn("country (package)", human)
            self.assertIn("Applicable country", human)
            parsed = json.loads(self.run_kb(root, "schema", "--json").stdout)
            self.assertEqual("kb-core@2", parsed["extends"])
            self.assertEqual(700, parsed["fields"]["country"]["search"]["weight"])
            self.assertEqual("default", parsed["fields"]["country"]["normalization"])

    def test_search_and_list_use_generic_filter_or_within_and_and_across(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            self.write(root, "info/16T.md", entry("info", "Intercompany", {"country": ["JP", "DE"], "capability": ["16T"]}, ["source/official.md"]))
            self.write(root, "info/2UP.md", entry("info", "Brazil tax", {"country": ["BR"], "capability": ["2UP"]}, ["source/official.md"]))
            filtered = self.run_kb(root, "search", "--filter", "country=JP", "--filter", "country=DE", "--filter", "capability=16T").stdout
            self.assertIn("info/16T.md", filtered); self.assertNotIn("info/2UP.md", filtered)
            listed = self.run_kb(root, "list", "info", "--filter", "country=BR").stdout
            self.assertIn("info/2UP.md", listed); self.assertNotIn("info/16T.md", listed)

    def test_filters_reject_unknown_or_non_filterable_fields_and_empty_query_needs_filter(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            unknown = self.run_kb(root, "search", "x", "--filter", "missing=x", check=False)
            self.assertEqual(2, unknown.returncode); self.assertIn("unknown metadata field", unknown.stderr)
            non_filterable = self.run_kb(root, "search", "x", "--filter", "note=x", check=False)
            self.assertEqual(2, non_filterable.returncode); self.assertIn("not filterable", non_filterable.stderr)
            empty = self.run_kb(root, "search", "", check=False)
            self.assertEqual(2, empty.returncode); self.assertIn("requires a query or --filter", empty.stderr)

    def test_metadata_weight_controls_keyword_order_and_alias_expands_keyword_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            self.write(root, "info/title-japan.md", entry("info", "Japan overview", {"country": ["DE"]}, ["source/official.md"]))
            self.write(root, "info/metadata-jp.md", entry("info", "Overview", {"country": ["JP"], "capability": ["16T"]}, ["source/official.md"]))
            keyword = self.run_kb(root, "search", "日本").stdout.splitlines()
            paths = [line for line in keyword if line.startswith("info/")]
            self.assertEqual("info/metadata-jp.md - Overview", paths[0])
            exact = self.run_kb(root, "search", "--filter", "country=日本").stdout
            self.assertIn("No matches.", exact)

    def test_directory_names_do_not_participate_in_country_keyword_search(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            self.write(root, "info/JP/misleading-path.md", entry("info", "General overview", {"country": ["DE"]}, ["source/official.md"]))
            result = self.run_kb(root, "search", "JP").stdout
            self.assertIn("No matches.", result)

    def test_read_meta_only_and_trace_use_v2_core_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            self.write(root, "info/base.md", entry("info", "Base", {"country": ["JP"]}, ["source/official.md"]))
            self.write(root, "knowledge/result.md", entry("knowledge", "Result", {"capability": ["16T"]}, depends_on=["info/base.md"]))
            meta = self.run_kb(root, "read", "info/base.md", "--meta-only").stdout
            self.assertIn("metadata:", meta); self.assertIn("country:", meta)
            trace = self.run_kb(root, "trace", "knowledge/result.md").stdout
            self.assertIn("info/base.md - Base", trace); self.assertIn("source/official.md", trace)

    def test_static_v2_fixture_exercises_schema_search_list_read_and_scan(self):
        self.assertIn("country (package)", self.run_kb(FIXTURE, "schema").stdout)
        self.assertIn("info/16T.md", self.run_kb(FIXTURE, "search", "日本").stdout)
        listed = self.run_kb(FIXTURE, "list", "info", "--filter", "country=BR").stdout
        self.assertIn("info/2UP.md", listed); self.assertNotIn("info/16T.md", listed)
        self.assertIn("metadata:", self.run_kb(FIXTURE, "read", "info/16T.md", "--meta-only").stdout)
        self.assertIn("OK", self.run_kb(FIXTURE, "scan").stdout)


if __name__ == "__main__":
    unittest.main()
