import subprocess
import sys
import tempfile
import unittest
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "knowledge-db" / "scripts"
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

    def test_init_creates_kb_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")

            root = Path(tmp) / ".kb"
            self.assertTrue((root / "source").is_dir())
            self.assertTrue((root / "info").is_dir())
            self.assertTrue((root / "knowledge").is_dir())

    def test_new_entries_list_tree_search_and_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")
            source = Path(tmp) / ".kb" / "source" / "sap" / "Configuration Activity.xlsm"
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
            )

            result = self.run_kb(tmp, "scan", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing dependency", result.stdout.lower())
            self.assertIn("info/nope.md", result.stdout)

    def test_create_with_body_file_and_read_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")
            source = Path(tmp) / ".kb" / "source" / "manual.md"
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

            entry = Path(tmp) / ".kb" / "info" / "manual" / "alpha.md"
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

    def test_enhanced_search_all_any_tags_and_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_kb(tmp, "init")
            source = Path(tmp) / ".kb" / "source" / "manual.md"
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
            source = Path(tmp) / ".kb" / "source" / "manual.md"
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
            info_path = Path(tmp) / ".kb" / "info" / "manual" / "base-info.md"
            info_text = info_path.read_text(encoding="utf-8").replace(
                "updated: 2026-07-06", "updated: 2999-01-01"
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
            source = Path(tmp) / ".kb" / "source" / "manual.md"
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
                "--body",
                "PowerShell wrapper body",
                env=env,
            )

            result = self.run_script(command, tmp, "list", "info", env=env)
            self.assertIn("info/manual/from-powershell.md - Info From PowerShell", result.stdout)

    def test_sh_wrapper_forwards_to_kb_py(self):
        shell = find_sh_shell()
        if shell is None:
            self.skipTest("sh-compatible shell is not available")
        env = os.environ.copy()
        env["KB_PYTHON"] = sys.executable.replace("\\", "/")
        command = [shell, KB_SH.as_posix()]

        with tempfile.TemporaryDirectory() as tmp:
            self.run_script(command, tmp, "init", env=env)
            source = Path(tmp) / ".kb" / "source" / "manual.md"
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
                "--body",
                "sh wrapper body",
                env=env,
            )

            result = self.run_script(command, tmp, "list", "info", env=env)
            self.assertIn("info/manual/from-sh.md - Info From Sh", result.stdout)


if __name__ == "__main__":
    unittest.main()
