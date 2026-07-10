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
SKELETON = ROOT / "skills" / "knowledge-db-maintain" / "assets" / "package-skeleton"
SKELETON_ASSETS = (
    "kb-package-schema.json",
    "source/.gitkeep",
    "info/.gitkeep",
    "knowledge/.gitkeep",
    "scripts/README.md",
    "scripts/check_package.py",
    "scripts/catalog/__init__.py",
    "scripts/catalog/build_catalog_from_service.mjs",
    "scripts/catalog/metadata.py",
    "scripts/catalog/sqlite_smoke.py",
    "scripts/catalog/test_metadata.py",
    "scripts/catalog/write_artifact_metadata.py",
    ".github/workflows/catalog-artifact.yml",
)


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
            "type": "string", "multiple": False, "description": "Release", "filterable": True,
            "search": {"enabled": False, "weight": 0},
        },
        "note": {
            "type": "string", "multiple": False, "description": "Non-queryable note", "filterable": False,
            "search": {"enabled": False, "weight": 0},
        },
    },
}


def entry(kind, title, metadata=None, source=None, depends_on=None, status="active"):
    core = ["schema: kb-entry@2", f"kind: {kind}", f"title: {title}", f"status: {status}", "updated: 2026-07-10"]
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
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        result = subprocess.run(
            [sys.executable, str(KB), "--kb", str(root), *args],
            capture_output=True, text=True, encoding="utf-8", errors="strict", env=env,
        )
        if check and result.returncode:
            self.fail(f"kb {' '.join(args)} returned {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result

    def make_package(self, root):
        for name in ("source", "info", "knowledge"):
            (root / name).mkdir()
        (root / "kb-package-schema.json").write_text(json.dumps(SCHEMA), encoding="utf-8")
        (root / "source" / "official.md").write_text("official", encoding="utf-8")
        checker = root / "scripts" / "check_package.py"
        checker.parent.mkdir()
        checker.write_bytes((SKELETON / "scripts" / "check_package.py").read_bytes())

    def write(self, root, rel, content):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_init_materializes_the_complete_generic_package_skeleton(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = self.run_kb(root, "init")

            self.assertIn("Initialized", result.stdout)
            for directory in ("source", "info", "knowledge"):
                self.assertTrue((root / directory).is_dir(), directory)
            for asset in SKELETON_ASSETS:
                path = root / asset
                self.assertTrue(path.is_file(), asset)
                self.assertNotIn("s4hana", path.read_text(encoding="utf-8").lower(), asset)
            schema = json.loads((root / "kb-package-schema.json").read_text(encoding="utf-8"))
            self.assertEqual("kb-package-schema@2", schema["schema"])
            self.assertEqual({}, schema["fields"])
            check = subprocess.run(
                [sys.executable, str(root / "scripts" / "check_package.py"), "--kb", str(root)],
                capture_output=True, text=True, encoding="utf-8", errors="strict",
            )
            self.assertEqual(0, check.returncode, check.stderr)
            self.assertIn("OK:", check.stdout)
            self.assertIn("Initialized", self.run_kb(root, "init").stdout)

    def test_init_refuses_to_overwrite_a_changed_skeleton_asset(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.run_kb(root, "init")
            schema_path = root / "kb-package-schema.json"
            schema_path.write_text('{"changed": true}\n', encoding="utf-8")

            result = self.run_kb(root, "init", check=False)

            self.assertEqual(2, result.returncode)
            self.assertIn("refusing to overwrite modified package asset: kb-package-schema.json", result.stderr)
            self.assertEqual('{"changed": true}\n', schema_path.read_text(encoding="utf-8"))

    def test_init_refuses_a_directory_at_an_asset_path_without_writing_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts" / "check_package.py").mkdir(parents=True)

            result = self.run_kb(root, "init", check=False)

            self.assertEqual(2, result.returncode)
            self.assertIn("refusing to overwrite modified package asset: scripts/check_package.py", result.stderr)
            self.assertFalse((root / "kb-package-schema.json").exists())
            self.assertFalse((root / "source").exists())

    def test_init_runs_the_materialized_checker_and_propagates_its_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "info/bad.md", "not frontmatter\n")

            result = self.run_kb(root, "init", check=False)

            self.assertEqual(2, result.returncode)
            self.assertIn("missing YAML frontmatter", result.stderr)
            self.assertTrue((root / "scripts" / "check_package.py").is_file())

    def test_schema_and_scan_reject_the_same_invalid_field_contracts(self):
        invalid_fields = {
            "core conflict": ("title", {"type": "string", "multiple": False, "description": "Title", "filterable": True, "search": {"enabled": True, "weight": 1}}),
            "invalid key": ("bad key", {"type": "string", "multiple": False, "description": "Bad", "filterable": True, "search": {"enabled": True, "weight": 1}}),
            "unknown normalizer": ("country", {"type": "string", "multiple": True, "description": "Country", "filterable": True, "normalization": "unknown", "search": {"enabled": True, "weight": 1}}),
            "excessive weight": ("country", {"type": "string", "multiple": True, "description": "Country", "filterable": True, "search": {"enabled": True, "weight": 1001}}),
            "disabled weighted field": ("country", {"type": "string", "multiple": True, "description": "Country", "filterable": True, "search": {"enabled": False, "weight": 1}}),
        }
        for label, (field_name, definition) in invalid_fields.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); self.run_kb(root, "init")
                (root / "kb-package-schema.json").write_text(json.dumps({
                    "schema": "kb-package-schema@2", "extends": "kb-core@2", "fields": {field_name: definition},
                }), encoding="utf-8")
                self.assertEqual(2, self.run_kb(root, "schema", check=False).returncode)
                self.assertEqual(2, self.run_kb(root, "scan", check=False).returncode)

    def test_scan_and_validate_delegate_to_the_generated_package_checker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.run_kb(root, "init")
            schema_path = root / "kb-package-schema.json"
            schema_path.write_text(json.dumps({
                "schema": "kb-package-schema@2", "extends": "kb-core@2",
                "fields": {"country": {"type": "string", "description": "Country", "filterable": True,
                                       "search": {"enabled": True, "weight": 700}}},
            }), encoding="utf-8")

            schema = self.run_kb(root, "scan", check=False)
            self.assertEqual(2, schema.returncode)
            self.assertIn("must declare boolean multiple", schema.stderr)

            schema_path.write_text(json.dumps({
                "schema": "kb-package-schema@2", "extends": "kb-core@2",
                "fields": {"tags": {"type": "string", "multiple": True, "description": "Tags",
                                    "filterable": True, "search": {"enabled": True, "weight": 620}}},
            }), encoding="utf-8")
            self.write(root, "info/product/2602/shared/item.md", entry("info", "Bad reference", {"tags": ["general"]}, ["source/missing.md"]))
            (root / "info" / "product" / "2602" / "unexpected").mkdir(parents=True)

            for command in ("scan", "validate"):
                result = self.run_kb(root, command, check=False)
                self.assertEqual(2, result.returncode)
                self.assertIn("local reference does not exist", result.stderr)
                self.assertIn("version directories may contain only shared/", result.stderr)

    def test_schema_rejects_non_string_or_incompletely_declared_package_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            schema_path = root / "kb-package-schema.json"
            schema_path.write_text(json.dumps({
                "schema": "kb-package-schema@2", "extends": "kb-core@2",
                "fields": {"rank": {"type": "number", "description": "Rank", "filterable": True,
                                    "search": {"enabled": True, "weight": 1}}},
            }), encoding="utf-8")

            result = self.run_kb(root, "schema", check=False)

            self.assertEqual(2, result.returncode)
            self.assertIn("field rank type must be string", result.stderr)

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
            self.assertEqual(2, result.returncode)
            self.assertIn("requires non-empty 'source' string list", result.stderr)

            self.write(root, "info/bad.md", entry("info", "Bad", {"country": "JP"}, ["source/official.md"]))
            result = self.run_kb(root, "scan", check=False)
            self.assertEqual(2, result.returncode)
            self.assertIn("metadata field 'country' must be a list of strings", result.stderr)

            self.write(root, "info/bad.md", entry("info", "Bad", {"country": ["JP"], "unknown": "x"}, ["source/official.md"]))
            result = self.run_kb(root, "scan", check=False)
            self.assertEqual(2, result.returncode)
            self.assertIn("metadata field 'unknown' is not declared", result.stderr)

    def test_scan_rejects_package_values_outside_nested_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            content = entry("info", "Bad top level", {"country": ["JP"]}, ["source/official.md"])
            content = content.replace("metadata:\n", "country: JP\nmetadata:\n")
            self.write(root, "info/bad-top-level.md", content)
            result = self.run_kb(root, "scan", check=False)
            self.assertEqual(2, result.returncode)
            self.assertIn("unexpected frontmatter field(s): country", result.stderr)

    def test_schema_lists_merged_core_and_package_fields_in_human_and_json_forms(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            human = self.run_kb(root, "schema").stdout
            self.assertIn("title (core)", human); self.assertIn("country (package)", human)
            self.assertIn("Applicable country", human)
            self.assertIn("required=", human); self.assertIn("normalization=default", human)
            self.assertIn("aliases=JP:Japan,日本", human)
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

    def test_filter_normalizes_declared_values_without_using_aliases(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            self.write(root, "info/jp.md", entry("info", "Japan entry", {"country": ["JP"]}, ["source/official.md"]))
            normalized = self.run_kb(root, "search", "--filter", "country=jp").stdout
            self.assertIn("info/jp.md", normalized)
            aliased = self.run_kb(root, "search", "--filter", "country=日本").stdout
            self.assertIn("No matches.", aliased)

    def test_queries_skip_invalid_entries_and_read_or_trace_reject_them(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            self.write(root, "info/valid.md", entry("info", "Valid", {"country": ["JP"]}, ["source/official.md"]))
            self.write(root, "info/invalid.md", entry("info", "Invalid", {"country": "JP"}, ["source/official.md"]))
            listed = self.run_kb(root, "list", "info", "--filter", "country=JP").stdout
            searched = self.run_kb(root, "search", "--filter", "country=JP").stdout
            self.assertIn("info/valid.md", listed); self.assertNotIn("info/invalid.md", listed)
            self.assertIn("info/valid.md", searched); self.assertNotIn("info/invalid.md", searched)
            read = self.run_kb(root, "read", "info/invalid.md", "--meta-only", check=False)
            trace = self.run_kb(root, "trace", "info/invalid.md", check=False)
            self.assertEqual(1, read.returncode); self.assertIn("metadata.country must be an array", read.stderr)
            self.assertEqual(1, trace.returncode); self.assertIn("metadata.country must be an array", trace.stderr)

    def test_scan_rejects_boolean_keyword_weights(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            schema_path = root / "kb-package-schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            schema["fields"]["country"]["search"]["weight"] = True
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            result = self.run_kb(root, "scan", check=False)
            self.assertEqual(2, result.returncode)
            self.assertIn("must declare integer search.weight from 0 to 1000", result.stderr)

    def test_real_package_normalizers_apply_to_schema_search_and_filters(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            schema_path = root / "kb-package-schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            schema["fields"]["tags"]["normalization"] = "keyword"
            schema["fields"]["country"]["normalization"] = "upper-case-code"
            schema["fields"]["capability"]["normalization"] = "upper-case-code"
            schema["fields"]["release"]["normalization"] = "release-code"
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            self.write(root, "info/16T.md", entry("info", "Intercompany", {"tags": ["sap-configuration"], "country": ["JP"], "capability": ["16T"], "release": '"2602"'}, ["source/official.md"]))
            self.assertIn("OK", self.run_kb(root, "scan").stdout)
            result = self.run_kb(root, "search", "16t", "--filter", "country=jp").stdout
            self.assertIn("info/16T.md", result)
            discovered = json.loads(self.run_kb(root, "schema", "--json").stdout)
            self.assertEqual("upper-case-code", discovered["fields"]["country"]["normalization"])

    def test_real_v2_entry_schema_and_yaml_sequence_indentation_are_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.make_package(root)
            self.write(root, "info/16T.md", """---
schema: kb-entry@2
kind: info
title: Intercompany
source:
- source/official.md
status: active
updated: '2026-07-10'
metadata:
  country:
  - JP
  capability:
  - 16T
---

# Intercompany
""")
            self.assertIn("OK", self.run_kb(root, "scan").stdout)
            self.assertIn("info/16T.md", self.run_kb(root, "search", "16T", "--filter", "country=jp").stdout)

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
