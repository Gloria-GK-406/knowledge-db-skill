from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _join_url(base_url: str, object_key: str) -> str:
    return f"{base_url.rstrip('/')}/{object_key.lstrip('/')}"


def write_artifact_metadata(
    *,
    out_dir: Path,
    source_repo: str,
    source_ref: str,
    source_revision: str,
    version: str,
    package_name: str,
    public_base_url: str,
    object_prefix: str,
    latest_object_key: str,
    builder_metadata_path: Path,
    timings_path: Path,
) -> None:
    catalog_gz = out_dir / "catalog.sqlite.gz"
    if not catalog_gz.exists():
        raise FileNotFoundError(f"missing compressed catalog: {catalog_gz}")

    builder_metadata = _read_json(builder_metadata_path)
    timings = _read_json(timings_path)
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    compressed_bytes = catalog_gz.stat().st_size
    sqlite_path = out_dir / "catalog.sqlite"
    sqlite_bytes = sqlite_path.stat().st_size if sqlite_path.exists() else 0

    validation = builder_metadata.get("validation", {})
    generator = builder_metadata.get(
        "generator",
        {
            "name": "knowledge-service-catalog-builder",
            "version": source_revision,
        },
    )
    builder_timings = builder_metadata.get("timingsMs", {})
    merged_timings = {
        "checkout": int(timings.get("checkout", 0)),
        "setup": int(timings.get("setup", 0)),
        "validate": int(builder_timings.get("validate", timings.get("validate", 0))),
        "buildCatalog": int(builder_timings.get("buildCatalog", timings.get("buildCatalog", 0))),
        "compress": int(timings.get("compress", 0)),
        "upload": int(timings.get("upload", 0)),
        "total": int(timings.get("total", 0)),
    }

    manifest = {
        "schema": "kb-catalog-artifact@1",
        "sourceRepo": source_repo,
        "sourceRevision": source_revision,
        "sourceRef": source_ref,
        "version": version,
        "packageName": package_name,
        "generator": generator,
        "catalog": {
            "path": "catalog.sqlite.gz",
            "sha256": sha256_file(catalog_gz),
            "bytes": compressed_bytes,
            "compression": "gzip",
        },
        "validation": {
            "ok": bool(validation.get("ok", False)),
            "errorCount": int(validation.get("errorCount", 0)),
            "warningCount": int(validation.get("warningCount", 0)),
            "entryCount": int(validation.get("entryCount", 0)),
        },
        "createdAt": created_at,
    }
    metrics = {
        "schema": "kb-catalog-build-metrics@1",
        "sourceRevision": source_revision,
        "version": version,
        "entries": manifest["validation"]["entryCount"],
        "bytes": {
            "catalogSqlite": sqlite_bytes,
            "catalogCompressed": compressed_bytes,
        },
        "timingsMs": merged_timings,
    }
    manifest_key = f"{object_prefix.rstrip('/')}/manifest.json"
    latest = {
        "schema": "kb-catalog-latest@1",
        "sourceRepo": source_repo,
        "sourceRef": source_ref,
        "sourceRevision": source_revision,
        "version": version,
        "latestKey": latest_object_key,
        "manifestKey": manifest_key,
        "manifestUrl": _join_url(public_base_url, manifest_key),
        "createdAt": created_at,
    }

    _write_json(out_dir / "manifest.json", manifest)
    _write_json(out_dir / "build-metrics.json", metrics)
    _write_json(out_dir / "latest.json", latest)
