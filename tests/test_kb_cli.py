import subprocess
import sys
import tempfile
import unittest
import os
import shutil
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "knowledge-db-maintain" / "scripts"
KB = SCRIPT_DIR / "kb.py"
KB_PS1 = SCRIPT_DIR / "kb.ps1"
KB_SH = SCRIPT_DIR / "kb.sh"


def find_sh_shell():
    candidates = []
    for name in ("bash", "sh"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    candidates.extend(
        [
            Path(r"C:\Program Files\Git\bin\bash.exe"),
            Path(r"C:\Program Files\Git\usr\bin\sh.exe"),
            Path(r"C:\Program Files (x86)\Git\bin\bash.exe"),
            Path(r"C:\Program Files (x86)\Git\usr\bin\sh.exe"),
        ]
    )
    for candidate in candidates:
        if not candidate.exists():
            continue
        normalized = str(candidate).lower()
        if normalized.endswith(r"\windows\system32\bash.exe"):
            continue
        return str(candidate)
    return None


class KbCliTests(unittest.TestCase):
    def run_kb(self, cwd, *args, check=True):
        result = subprocess.run(
            [sys.executable, str(KB), *args],
            cwd=cwd,
            text=True,
            capture_output=True,
        )
        if check and result.returncode != 0:
            self.fail(
                f"kb.py {' '.join(args)} failed\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )
        return result

    def run_script(self, command, cwd, *args, env=None, check=True):
        result = subprocess.run(
            [*command, *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
        )
        if check and result.returncode != 0:
            self.fail(
                f"{' '.join(str(part) for part in command + list(args))} failed\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )
        return result

    def run_script_bytes(self, command, cwd, *args, env=None, check=True):
        result = subprocess.run(
            [*command, *args],
            cwd=cwd,
            env=env,
            capture_output=True,
        )
        if check and result.returncode != 0:
            self.fail(
                f"{' '.join(str(part) for part in command + list(args))} failed\n"
                f"stdout:\n{result.stdout!r}\n"
                f"stderr:\n{result.stderr!r}"
            )
        return result

    def test_init_creates_kb_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")

            root = Path(tmp)
            self.assertTrue((root / "source").is_dir())
            self.assertTrue((root / "info").is_dir())
            self.assertTrue((root / "knowledge").is_dir())

    def test_global_kb_option_can_appear_after_command_or_between_args(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "custom-kb"
            self.run_kb(tmp, "init", "--kb", str(root))
            self.assertTrue((root / "source").is_dir())

            source = root / "source" / "manual.md"
            source.write_text("raw source", encoding="utf-8")
            self.run_kb(
                tmp,
                "new-info",
                "manual/unordered",
                "--title",
                "Unordered Args",
                "--kb",
                str(root),
                "--source",
                "source/manual.md",
                "--tag",
                "args",
            )

            list_result = self.run_kb(tmp, "list", "--kb", str(root), "info")
            self.assertIn("info/manual/unordered.md - Unordered Args", list_result.stdout)

            scan_result = self.run_kb(tmp, f"--kb={root}", "scan")
            self.assertIn("OK", scan_result.stdout)

    def test_new_entries_list_tree_search_and_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")
            source = Path(tmp) / "source" / "sap" / "Configuration Activity.xlsm"
            source.parent.mkdir(parents=True)
            source.write_text("placeholder", encoding="utf-8")

            self.run_kb(
                tmp,
                "new-info",
                "sap/s4hana-cloud/delivery-management-activities",
                "--title",
                "Delivery Management 配置活动整理",
                "--source",
                "source/sap/Configuration Activity.xlsm#sheet=2602 S4H Cloud",
                "--tag",
                "sap",
                "--tag",
                "delivery",
            )
            self.run_kb(
                tmp,
                "new-knowledge",
                "sap/s4hana-cloud/how-to-construct-delivery-cbc",
                "--title",
                "如何构建交货业务的 CBC 配置",
                "--depends-on",
                "info/sap/s4hana-cloud/delivery-management-activities.md",
                "--tag",
                "cbc",
                "--status",
                "draft",
            )

            list_result = self.run_kb(tmp, "list", "knowledge")
            self.assertIn("knowledge/sap/s4hana-cloud/how-to-construct-delivery-cbc.md", list_result.stdout)
            self.assertIn("如何构建交货业务的 CBC 配置", list_result.stdout)

            tree_dirs = self.run_kb(tmp, "tree", "info")
            self.assertIn("sap/", tree_dirs.stdout)
            self.assertNotIn("delivery-management-activities.md", tree_dirs.stdout)

            tree_files = self.run_kb(tmp, "tree", "info", "--files", "--titles")
            self.assertIn("delivery-management-activities.md - Delivery Management 配置活动整理", tree_files.stdout)

            search_result = self.run_kb(tmp, "search", "交货", "--kind", "knowledge")
            self.assertIn("如何构建交货业务的 CBC 配置", search_result.stdout)

            scan_result = self.run_kb(tmp, "scan")
            self.assertIn("OK", scan_result.stdout)

    def test_scan_reports_missing_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")
            self.run_kb(
                tmp,
                "new-knowledge",
                "sap/missing-dependency",
                "--title",
                "Missing dependency",
                "--depends-on",
                "info/nope.md",
                "--tag",
                "test",
            )

            result = self.run_kb(tmp, "scan", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing dependency", result.stdout.lower())
            self.assertIn("info/nope.md", result.stdout)

    def test_scan_accepts_accessible_web_source_and_warns_on_unreachable_url(self):
        class Handler(BaseHTTPRequestHandler):
            def do_HEAD(self):
                self.send_response(200)
                self.end_headers()

            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"web source")

            def log_message(self, _format, *_args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                self.run_kb(tmp, "init")
                url = f"http://127.0.0.1:{server.server_port}/docs/page?version=1#section"
                self.run_kb(
                    tmp,
                    "new-info",
                    "web/access",
                    "--title",
                    "Web Source Info",
                    "--source",
                    url,
                    "--tag",
                    "web",
                    "--body",
                    "# Web Source Info\n\n## Scope\n\nWeb access smoke test.\n\n## Facts\n\nCollected from a web page.\n\n## Notes\n\nLocal test server source.\n",
                )

                scan = self.run_kb(tmp, "scan")
                self.assertIn("OK", scan.stdout)

                self.run_kb(
                    tmp,
                    "new-knowledge",
                    "web/derived",
                    "--title",
                    "Derived From Web",
                    "--depends-on",
                    "info/web/access.md",
                    "--tag",
                    "web",
                )
                impact = self.run_kb(tmp, "impact", url)
                self.assertIn("info/web/access.md - Web Source Info", impact.stdout)
                self.assertIn("knowledge/web/derived.md - Derived From Web", impact.stdout)

                self.run_kb(
                    tmp,
                    "new-info",
                    "web/missing",
                    "--title",
                    "Missing Web Source",
                    "--source",
                    "http://127.0.0.1:1/not-there",
                    "--tag",
                    "web",
                    "--force",
                )

                missing = self.run_kb(tmp, "scan", check=False)
                self.assertEqual(missing.returncode, 0)
                self.assertIn("source URL not accessible", missing.stdout)
                self.assertIn("http://127.0.0.1:1/not-there", missing.stdout)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    def test_create_with_body_file_and_read_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")
            source = Path(tmp) / "source" / "manual.md"
            source.write_text("raw source", encoding="utf-8")
            body = Path(tmp) / "body.md"
            body.write_text("# Custom Body\n\nAlpha beta gamma.\n", encoding="utf-8")

            self.run_kb(
                tmp,
                "new-info",
                "manual/alpha",
                "--title",
                "Alpha Info",
                "--source",
                "source/manual.md",
                "--tag",
                "alpha",
                "--body-file",
                str(body),
            )

            entry = Path(tmp) / "info" / "manual" / "alpha.md"
            text = entry.read_text(encoding="utf-8")
            self.assertIn("# Custom Body", text)
            self.assertNotIn("# Alpha Info", text)

            read_all = self.run_kb(tmp, "read", "info/manual/alpha.md")
            self.assertIn("kind: info", read_all.stdout)
            self.assertIn("Alpha beta gamma.", read_all.stdout)

            read_body = self.run_kb(tmp, "read", "info/manual/alpha.md", "--body-only")
            self.assertNotIn("kind: info", read_body.stdout)
            self.assertIn("# Custom Body", read_body.stdout)

            read_meta = self.run_kb(tmp, "read", "info/manual/alpha.md", "--meta-only")
            self.assertIn("title: Alpha Info", read_meta.stdout)
            self.assertNotIn("Alpha beta gamma.", read_meta.stdout)

    def test_read_line_context_and_markdown_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")
            source = Path(tmp) / "source" / "templates.md"
            source.write_text("raw source", encoding="utf-8")
            body = Path(tmp) / "templates-body.md"
            body.write_text(
                "\n".join(
                    [
                        "# Expert Configuration Templates",
                        "",
                        "## J80 Basic Template",
                        "basic template line",
                        "",
                        "## J90 Expert Template",
                        "J90 overview line",
                        "business catalog assignment for J90",
                        "J90 closing line",
                        "### J90 Details",
                        "nested detail stays in J90",
                        "",
                        "## J91 Follow Up Template",
                        "J91 should not be included",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            self.run_kb(
                tmp,
                "new-info",
                "manual/templates",
                "--title",
                "Template Info",
                "--source",
                "source/templates.md",
                "--tag",
                "template",
                "--body-file",
                str(body),
            )

            entry = Path(tmp) / "info" / "manual" / "templates.md"
            target_line = next(
                index
                for index, line in enumerate(entry.read_text(encoding="utf-8").splitlines(), start=1)
                if "business catalog assignment" in line
            )

            search = self.run_kb(tmp, "search", "business catalog", "--kind", "info", "--context", "0")
            self.assertIn(f"  {target_line}: business catalog assignment for J90", search.stdout)

            line_read = self.run_kb(
                tmp,
                "read",
                "info/manual/templates.md",
                "--line",
                str(target_line),
                "--context",
                "1",
            )
            self.assertIn(f"{target_line - 1}: J90 overview line", line_read.stdout)
            self.assertIn(f"{target_line}: business catalog assignment for J90", line_read.stdout)
            self.assertIn(f"{target_line + 1}: J90 closing line", line_read.stdout)
            self.assertNotIn("J91 should not be included", line_read.stdout)

            section = self.run_kb(tmp, "read", "info/manual/templates.md", "--section", "J90")
            self.assertIn("## J90 Expert Template", section.stdout)
            self.assertIn("nested detail stays in J90", section.stdout)
            self.assertNotIn("## J91 Follow Up Template", section.stdout)
            self.assertNotIn("J91 should not be included", section.stdout)

    def test_read_section_context_includes_adjacent_section_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")
            source = Path(tmp) / "source" / "manual.md"
            source.write_text("raw source", encoding="utf-8")
            body = Path(tmp) / "facts-body.md"
            body.write_text(
                "\n".join(
                    [
                        "# Section Context",
                        "",
                        "## Scope",
                        "scope body should stay out",
                        "",
                        "## Facts",
                        "important fact stays in",
                        "",
                        "## Notes",
                        "notes body should stay out",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            self.run_kb(
                tmp,
                "new-info",
                "manual/section-context",
                "--title",
                "Section Context",
                "--source",
                "source/manual.md",
                "--tag",
                "section",
                "--body-file",
                str(body),
            )

            section = self.run_kb(
                tmp,
                "read",
                "info/manual/section-context.md",
                "--section",
                "Facts",
                "--context",
                "1",
            )
            self.assertIn("## Scope", section.stdout)
            self.assertIn("## Facts", section.stdout)
            self.assertIn("important fact stays in", section.stdout)
            self.assertIn("## Notes", section.stdout)
            self.assertNotIn("scope body should stay out", section.stdout)
            self.assertNotIn("notes body should stay out", section.stdout)

            conflict = self.run_kb(
                tmp,
                "read",
                "info/manual/section-context.md",
                "--meta-only",
                "--section",
                "Facts",
                check=False,
            )
            self.assertEqual(conflict.returncode, 2)
            self.assertIn("Allowed combinations", conflict.stderr)
            self.assertIn("--section TEXT --context N", conflict.stderr)

    def test_empty_search_query_reports_browsing_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")

            result = self.run_kb(tmp, "search", "", check=False)

            self.assertEqual(result.returncode, 2)
            self.assertIn("Empty q is not supported. Use list or tree for browsing.", result.stderr)

    def test_search_ranks_title_tag_slug_and_body_with_normalized_phrases(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")
            source = Path(tmp) / "source" / "manual.md"
            source.write_text("raw source", encoding="utf-8")

            self.run_kb(
                tmp,
                "new-info",
                "aaa/body-only",
                "--title",
                "Body Only",
                "--source",
                "source/manual.md",
                "--tag",
                "reference",
                "--body",
                "# Body Only\n\n## Scope\n\nBody mentions CBC configuration.\n\n## Facts\n\nbody match.\n\n## Notes\n\nnone.\n",
                "--status",
                "active",
            )
            self.run_kb(
                tmp,
                "new-info",
                "bbb/tag-match",
                "--title",
                "Tag Match",
                "--source",
                "source/manual.md",
                "--tag",
                "cbc-configuration",
                "--body",
                "# Tag Match\n\n## Scope\n\nNo body phrase.\n\n## Facts\n\nmetadata match.\n\n## Notes\n\nnone.\n",
                "--status",
                "active",
            )
            self.run_kb(
                tmp,
                "new-info",
                "cbc_configuration/slug-match",
                "--title",
                "Slug Match",
                "--source",
                "source/manual.md",
                "--tag",
                "reference",
                "--body",
                "# Slug Match\n\n## Scope\n\nNo body phrase.\n\n## Facts\n\npath match.\n\n## Notes\n\nnone.\n",
                "--status",
                "active",
            )
            self.run_kb(
                tmp,
                "new-knowledge",
                "zzz/title-match",
                "--title",
                "CBC Configuration",
                "--depends-on",
                "info/aaa/body-only.md",
                "--tag",
                "reference",
                "--body",
                "# CBC Configuration\n\n## Problem\n\nTitle match.\n\n## Conclusion\n\nUse the title.\n\n## Limits\n\nnone.\n\n## Reasoning\n\nfrom info.\n",
                "--status",
                "active",
            )

            result = self.run_kb(tmp, "search", "cbc configuration")
            result_lines = [line for line in result.stdout.splitlines() if ".md - " in line]

            self.assertEqual(
                result_lines,
                [
                    "knowledge/zzz/title-match.md - CBC Configuration",
                    "info/bbb/tag-match.md - Tag Match",
                    "info/cbc_configuration/slug-match.md - Slug Match",
                    "info/aaa/body-only.md - Body Only",
                ],
            )

            tag_phrase = self.run_kb(tmp, "search", "cbc configuration", "--tag", "cbc_configuration")
            self.assertIn("info/bbb/tag-match.md - Tag Match", tag_phrase.stdout)

    def test_read_and_search_accept_utf8_sig_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")
            source = Path(tmp) / "source" / "manual.md"
            source.write_text("raw source", encoding="utf-8")
            entry = Path(tmp) / "info" / "manual" / "bom.md"
            entry.parent.mkdir(parents=True)
            entry.write_text(
                "\ufeff---\n"
                "schema: kb-info@1\n"
                "kind: info\n"
                "title: BOM Info\n"
                "source:\n"
                "  - source/manual.md\n"
                "status: active\n"
                "updated: 2026-07-06\n"
                "tags:\n"
                "  - bom\n"
                "---\n\n"
                "# BOM Info\n\n"
                "needle appears here\n",
                encoding="utf-8",
            )

            read_result = self.run_kb(tmp, "read", "info/manual/bom.md", "--head", "3")
            self.assertIn("kind: info", read_result.stdout)

            search_result = self.run_kb(tmp, "search", "needle", "--kind", "info", "--context", "0")
            self.assertIn("info/manual/bom.md - BOM Info", search_result.stdout)
            self.assertIn("needle appears here", search_result.stdout)

    def test_new_entry_quotes_yaml_ambiguous_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")
            source = Path(tmp) / "source" / "manual.md"
            source.write_text("raw source", encoding="utf-8")

            self.run_kb(
                tmp,
                "new-info",
                "manual/scope-item",
                "--title",
                "Scope Item",
                "--source",
                "source/manual.md",
                "--tag",
                "1e1",
                "--tag",
                "287",
            )

            entry = Path(tmp) / "info" / "manual" / "scope-item.md"
            text = entry.read_text(encoding="utf-8")
            self.assertIn('  - "1e1"', text)
            self.assertIn('  - "287"', text)
            self.assertIn("OK", self.run_kb(tmp, "scan").stdout)

    def test_scan_rejects_server_parsed_non_string_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")
            source = Path(tmp) / "source" / "manual.md"
            source.write_text("raw source", encoding="utf-8")
            entry = Path(tmp) / "info" / "manual" / "scope-item.md"
            entry.parent.mkdir(parents=True)
            entry.write_text(
                "---\n"
                "schema: kb-info@1\n"
                "kind: info\n"
                "title: Scope Item\n"
                "source:\n"
                "  - source/manual.md\n"
                "status: active\n"
                "updated: 2026-07-07\n"
                "tags:\n"
                "  - 1e1\n"
                "---\n\n"
                "# Scope Item\n\n"
                "## Scope\n\n"
                "scope\n\n"
                "## Facts\n\n"
                "facts\n\n"
                "## Notes\n\n"
                "notes\n",
                encoding="utf-8",
            )

            result = self.run_kb(tmp, "scan", check=False)

            self.assertEqual(result.returncode, 1)
            self.assertIn("tags must contain only strings", result.stdout)

    def test_enhanced_search_all_any_tags_and_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")
            source = Path(tmp) / "source" / "manual.md"
            source.write_text("raw source", encoding="utf-8")
            body = Path(tmp) / "body.md"
            body.write_text("line one\nshipping point\nbusiness catalog\nlast line\n", encoding="utf-8")
            self.run_kb(
                tmp,
                "new-info",
                "manual/searchable",
                "--title",
                "Searchable Info",
                "--source",
                "source/manual.md",
                "--tag",
                "delivery",
                "--tag",
                "cbc",
                "--body-file",
                str(body),
            )

            result = self.run_kb(
                tmp,
                "search",
                "--kind",
                "info",
                "--tag",
                "delivery",
                "--all",
                "shipping,business",
                "--any",
                "catalog,route",
                "--context",
                "1",
            )
            self.assertIn("info/manual/searchable.md - Searchable Info", result.stdout)
            self.assertIn("shipping point", result.stdout)
            self.assertIn("business catalog", result.stdout)

            no_match = self.run_kb(tmp, "search", "--kind", "info", "--all", "shipping,missing")
            self.assertIn("No matches.", no_match.stdout)

    def test_trace_impact_and_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")
            source = Path(tmp) / "source" / "manual.md"
            source.write_text("raw source", encoding="utf-8")
            self.run_kb(
                tmp,
                "new-info",
                "manual/base-info",
                "--title",
                "Base Info",
                "--source",
                "source/manual.md",
                "--tag",
                "base",
            )
            info_path = Path(tmp) / "info" / "manual" / "base-info.md"
            info_text = info_path.read_text(encoding="utf-8").replace(
                f"updated: {date.today().isoformat()}", "updated: 2999-01-01"
            )
            info_path.write_text(info_text, encoding="utf-8")

            self.run_kb(
                tmp,
                "new-knowledge",
                "manual/derived",
                "--title",
                "Derived Knowledge",
                "--depends-on",
                "info/manual/base-info.md",
                "--tag",
                "base",
            )

            trace = self.run_kb(tmp, "trace", "knowledge/manual/derived.md")
            self.assertIn("knowledge/manual/derived.md - Derived Knowledge", trace.stdout)
            self.assertIn("info/manual/base-info.md - Base Info", trace.stdout)
            self.assertIn("source/manual.md", trace.stdout)

            impact_info = self.run_kb(tmp, "impact", "info/manual/base-info.md")
            self.assertIn("knowledge/manual/derived.md - Derived Knowledge", impact_info.stdout)

            impact_source = self.run_kb(tmp, "impact", "source/manual.md")
            self.assertIn("info/manual/base-info.md - Base Info", impact_source.stdout)
            self.assertIn("knowledge/manual/derived.md - Derived Knowledge", impact_source.stdout)

            stale = self.run_kb(tmp, "stale")
            self.assertIn("knowledge/manual/derived.md - Derived Knowledge", stale.stdout)
            self.assertIn("info/manual/base-info.md", stale.stdout)

    def test_powershell_wrapper_forwards_to_kb_py(self):
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is not available")
        env = os.environ.copy()
        env["KB_PYTHON"] = sys.executable
        command = [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(KB_PS1)]

        with tempfile.TemporaryDirectory() as tmp:
            self.run_script(command, tmp, "init", env=env)
            source = Path(tmp) / "source" / "manual.md"
            source.write_text("raw source", encoding="utf-8")
            self.run_script(
                command,
                tmp,
                "new-info",
                "manual/from-powershell",
                "--title",
                "Info From PowerShell",
                "--source",
                "source/manual.md",
                "--tag",
                "powershell",
                "--body",
                "PowerShell wrapper body",
                env=env,
            )

            result = self.run_script(command, tmp, "list", "info", env=env)
            self.assertIn("info/manual/from-powershell.md - Info From PowerShell", result.stdout)

    def test_powershell_wrapper_forces_utf8_for_python_output(self):
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is not available")
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["KB_PYTHON"] = sys.executable
            env["PYTHONIOENCODING"] = "cp936"
            env["PYTHONUTF8"] = "0"
            command = [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(KB_PS1),
            ]

            self.run_script_bytes(command, tmp, "init", env=env)
            source = Path(tmp) / "source" / "manual.md"
            source.write_text("raw source", encoding="utf-8")
            self.run_script_bytes(
                command,
                tmp,
                "new-info",
                "manual/utf8",
                "--title",
                "中文标题",
                "--source",
                "source/manual.md",
                "--tag",
                "utf8",
                env=env,
            )

            result = self.run_script_bytes(command, tmp, "list", "info", env=env)
            stdout = result.stdout.decode("utf-8")
            self.assertIn("info/manual/utf8.md - 中文标题", stdout)

    def test_powershell_wrapper_skips_unusable_python_candidate(self):
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is not available")
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            (bin_dir / "python.cmd").write_text("@echo off\r\nexit /b 88\r\n", encoding="utf-8")
            (bin_dir / "python3.cmd").write_text(
                f'@echo off\r\n"{sys.executable}" %*\r\n',
                encoding="utf-8",
            )
            env = os.environ.copy()
            env.pop("KB_PYTHON", None)
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
            command = [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(KB_PS1),
            ]

            result = self.run_script(command, tmp, "init", env=env)
            self.assertIn("Initialized", result.stdout)
            self.assertTrue((Path(tmp) / "source").is_dir())

    def test_sh_wrapper_forwards_to_kb_py(self):
        shell = find_sh_shell()
        if shell is None:
            self.skipTest("sh-compatible shell is not available")
        env = os.environ.copy()
        env["KB_PYTHON"] = sys.executable.replace("\\", "/")
        command = [shell, KB_SH.as_posix()]

        with tempfile.TemporaryDirectory() as tmp:
            self.run_script(command, tmp, "init", env=env)
            source = Path(tmp) / "source" / "manual.md"
            source.write_text("raw source", encoding="utf-8")
            self.run_script(
                command,
                tmp,
                "new-info",
                "manual/from-sh",
                "--title",
                "Info From Sh",
                "--source",
                "source/manual.md",
                "--tag",
                "sh",
                "--body",
                "sh wrapper body",
                env=env,
            )

            result = self.run_script(command, tmp, "list", "info", env=env)
            self.assertIn("info/manual/from-sh.md - Info From Sh", result.stdout)


if __name__ == "__main__":
    unittest.main()
