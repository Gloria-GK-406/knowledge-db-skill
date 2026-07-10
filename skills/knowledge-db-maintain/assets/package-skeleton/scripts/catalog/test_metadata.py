import gzip
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.catalog.metadata import write_artifact_metadata
from scripts.catalog.sqlite_smoke import smoke_catalog


def test_write_artifact_metadata_uses_catalog_hash_and_public_urls():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        out = root / "out"
        out.mkdir()
        catalog_gz = out / "catalog.sqlite.gz"
        with gzip.open(catalog_gz, "wb") as handle:
            handle.write(b"sqlite bytes")
        builder_metadata = out / "builder-metadata.json"
        builder_metadata.write_text(
            json.dumps(
                {
                    "generator": {
                        "name": "knowledge-package-catalog-builder",
                        "version": "abc123",
                    },
                    "validation": {
                        "ok": True,
                        "errorCount": 0,
                        "warningCount": 2,
                        "entryCount": 3,
                    },
                    "timingsMs": {
                        "validate": 11,
                        "buildCatalog": 22,
                    },
                    "catalog": {
                        "schema": "kb-catalog@2",
                        "schemaSha256": "a" * 64,
                    },
                }
            ),
            encoding="utf-8",
        )
        timings = out / "timings.json"
        timings.write_text(
            json.dumps(
                {
                    "checkout": 1,
                    "setup": 2,
                    "compress": 3,
                    "upload": 0,
                    "total": 40,
                }
            ),
            encoding="utf-8",
        )

        write_artifact_metadata(
            out_dir=out,
            source_repo="dlrk-dev/SAP-BTP-knowledge-db",
            source_ref="refs/tags/v0.1.0",
            source_revision="abc123",
            version="v0.1.0",
            package_name="SAP-BTP-knowledge-db",
            public_base_url="https://minio.example/public/",
            object_prefix="dlrk-dev/SAP-BTP-knowledge-db/v0.1.0",
            latest_object_key="dlrk-dev/SAP-BTP-knowledge-db/latest.json",
            builder_metadata_path=builder_metadata,
            timings_path=timings,
        )

        compressed_size = catalog_gz.stat().st_size
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        metrics = json.loads((out / "build-metrics.json").read_text(encoding="utf-8"))
        latest = json.loads((out / "latest.json").read_text(encoding="utf-8"))

    assert manifest["schema"] == "kb-catalog-artifact@2"
    assert manifest["sourceRevision"] == "abc123"
    assert manifest["version"] == "v0.1.0"
    assert manifest["catalog"]["path"] == "catalog.sqlite.gz"
    assert manifest["catalog"]["schema"] == "kb-catalog@2"
    assert manifest["catalog"]["schemaSha256"] == "a" * 64
    assert manifest["catalog"]["bytes"] == compressed_size
    assert len(manifest["catalog"]["sha256"]) == 64
    assert manifest["validation"]["entryCount"] == 3
    assert metrics["bytes"]["catalogCompressed"] == compressed_size
    assert metrics["timingsMs"]["validate"] == 11
    assert metrics["timingsMs"]["buildCatalog"] == 22
    assert latest["schema"] == "kb-catalog-latest@2"
    assert latest["version"] == "v0.1.0"
    assert latest["latestKey"] == "dlrk-dev/SAP-BTP-knowledge-db/latest.json"
    assert latest["manifestKey"] == "dlrk-dev/SAP-BTP-knowledge-db/v0.1.0/manifest.json"
    assert latest["manifestUrl"] == "https://minio.example/public/dlrk-dev/SAP-BTP-knowledge-db/v0.1.0/manifest.json"


def test_smoke_catalog_checks_required_tables_revision_and_entry_count():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "catalog.sqlite"
        connection = sqlite3.connect(db_path)
        connection.executescript(
            """
            CREATE TABLE packages (
              package_name TEXT PRIMARY KEY,
              root_path TEXT NOT NULL,
              revision TEXT NOT NULL,
              loaded_at TEXT NOT NULL
            );
            CREATE TABLE entries (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              package_name TEXT NOT NULL,
              entry_path TEXT NOT NULL,
              kind TEXT NOT NULL,
              title TEXT NOT NULL,
              status TEXT NOT NULL,
              updated TEXT NOT NULL,
              tags_json TEXT NOT NULL,
              body TEXT NOT NULL
            );
            INSERT INTO packages VALUES ('SAP-BTP-knowledge-db', '/kb', 'abc123', '2026-07-09T00:00:00Z');
            INSERT INTO entries (package_name, entry_path, kind, title, status, updated, tags_json, body)
              VALUES ('SAP-BTP-knowledge-db', 'info/example.md', 'info', 'Example', 'active', '2026-07-09', '[]', 'Body');
            """
        )
        connection.commit()
        connection.close()

        result = smoke_catalog(
            catalog_path=db_path,
            package_name="SAP-BTP-knowledge-db",
            source_revision="abc123",
            required_tables=("packages", "entries"),
        )

    assert result["entryCount"] == 1
    assert result["packageName"] == "SAP-BTP-knowledge-db"
    assert result["revision"] == "abc123"


def test_catalog_workflow_uses_only_package_local_producer():
    workflow = (
        Path(__file__).resolve().parents[2] / ".github" / "workflows" / "catalog-artifact.yml"
    ).read_text(encoding="utf-8")

    assert "python -m scripts.catalog.build_catalog" in workflow
    assert "knowledge-service" not in workflow
    assert "build_catalog_from_service.mjs" not in workflow


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    suite.addTest(unittest.FunctionTestCase(test_write_artifact_metadata_uses_catalog_hash_and_public_urls))
    suite.addTest(unittest.FunctionTestCase(test_smoke_catalog_checks_required_tables_revision_and_entry_count))
    suite.addTest(unittest.FunctionTestCase(test_catalog_workflow_uses_only_package_local_producer))
    return suite
