"""Build a kb-catalog@2 SQLite artifact from this package alone."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any

import yaml


ENTRY_KINDS = {"info", "knowledge"}
ENTRY_STATUSES = {"draft", "active", "deprecated", "rejected"}
FIELD_TYPES = {"string", "integer", "number", "boolean", "date"}
NORMALIZERS = {
    "string": {"text", "keyword", "upper-case-code", "lower-case-code", "release-code"},
    "integer": {"integer"},
    "number": {"number"},
    "boolean": {"boolean"},
    "date": {"date"},
}
ISO_COUNTRY_DIRECTORY = re.compile(r"^[A-Z]{2}$")
CORE_FIELDS = (
    ("kind", "string", False, ["info", "knowledge"], True, False, "keyword"),
    ("title", "string", False, ["info", "knowledge"], False, True, "text"),
    ("status", "string", False, ["info", "knowledge"], True, False, "keyword"),
    ("updated", "date", False, ["info", "knowledge"], True, False, "date"),
    ("source", "string", True, ["info"], False, False, "text"),
    ("depends_on", "string", True, ["knowledge"], False, False, "text"),
)


class CatalogBuildError(ValueError):
    """Raised for a package validation or compilation failure."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _normalise(value: Any, definition: dict[str, Any]) -> str | None:
    field_type = definition["type"]
    normalizer = definition["normalization"]
    if field_type == "string":
        if not isinstance(value, str) or not value.strip():
            return None
        text = value.strip()
        if normalizer == "text":
            return " ".join(text.lower().split())
        if normalizer == "keyword":
            return re.sub(r"[-_/\s]+", " ", text.lower()).strip()
        if normalizer in {"upper-case-code", "release-code"}:
            return text.upper()
        return text.lower()
    if field_type == "integer":
        return str(value) if isinstance(value, int) and not isinstance(value, bool) else None
    if field_type == "number":
        return str(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
    if field_type == "boolean":
        return str(value).lower() if isinstance(value, bool) else None
    if isinstance(value, str):
        try:
            date.fromisoformat(value)
        except ValueError:
            return None
        return value
    return None


def _load_schema(kb_root: Path) -> tuple[dict[str, dict[str, Any]], str, str]:
    path = kb_root / "kb-package-schema.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise CatalogBuildError(f"missing package schema: {path}") from error
    except json.JSONDecodeError as error:
        raise CatalogBuildError(f"invalid package schema JSON: {error.msg}") from error
    if not isinstance(raw, dict) or raw.get("schema") != "kb-package-schema@2" or raw.get("extends") != "kb-core@2":
        raise CatalogBuildError("package schema must be kb-package-schema@2 extending kb-core@2")
    raw_fields = raw.get("fields")
    if not isinstance(raw_fields, dict):
        raise CatalogBuildError("package schema fields must be an object")
    fields: dict[str, dict[str, Any]] = {}
    for key, definition in raw_fields.items():
        if not isinstance(key, str) or not key or key in {item[0] for item in CORE_FIELDS}:
            raise CatalogBuildError(f"invalid package field name: {key!r}")
        if not isinstance(definition, dict) or definition.get("type") not in FIELD_TYPES:
            raise CatalogBuildError(f"field {key!r} has an invalid type")
        field_type = definition["type"]
        if not isinstance(definition.get("multiple"), bool) or not isinstance(definition.get("filterable"), bool):
            raise CatalogBuildError(f"field {key!r} must declare multiple and filterable")
        if not isinstance(definition.get("description"), str) or not definition["description"].strip():
            raise CatalogBuildError(f"field {key!r} must have a description")
        if definition.get("normalization") not in NORMALIZERS[field_type]:
            raise CatalogBuildError(f"field {key!r} has incompatible normalization")
        required_for = definition.get("required_for", [])
        if not isinstance(required_for, list) or any(item not in ENTRY_KINDS for item in required_for) or len(set(required_for)) != len(required_for):
            raise CatalogBuildError(f"field {key!r} has invalid required_for")
        search = definition.get("search")
        if not isinstance(search, dict) or not isinstance(search.get("enabled"), bool):
            raise CatalogBuildError(f"field {key!r} must declare search.enabled")
        if search["enabled"]:
            if not isinstance(search.get("weight"), int) or isinstance(search["weight"], bool) or not 1 <= search["weight"] <= 1000:
                raise CatalogBuildError(f"field {key!r} must use a search weight from 1 through 1000")
        elif "weight" in search:
            raise CatalogBuildError(f"field {key!r} cannot set a disabled search weight")
        aliases = definition.get("aliases", {})
        if aliases and (field_type != "string" or not search["enabled"]):
            raise CatalogBuildError(f"field {key!r} aliases require a searchable string field")
        if not isinstance(aliases, dict) or any(
            not isinstance(canonical, str)
            or not isinstance(forms, list)
            or not forms
            or any(not isinstance(form, str) or not form.strip() for form in forms)
            for canonical, forms in aliases.items()
        ):
            raise CatalogBuildError(f"field {key!r} aliases must map strings to non-empty string lists")
        fields[key] = {
            "key": key,
            "type": field_type,
            "multiple": definition["multiple"],
            "required_for": required_for,
            "description": definition["description"].strip(),
            "filterable": definition["filterable"],
            "search": {"enabled": search["enabled"], **({"weight": search["weight"]} if search["enabled"] else {})},
            "normalization": definition["normalization"],
            "aliases": aliases,
        }
    canonical_json = _canonical_json(raw)
    return fields, canonical_json, hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def _parse_entry(path: Path, kb_root: Path, fields: dict[str, dict[str, Any]], package_name: str, revision: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise CatalogBuildError(f"{path}: missing YAML frontmatter")
    pieces = text.split("---", 2)
    if len(pieces) != 3:
        raise CatalogBuildError(f"{path}: unterminated YAML frontmatter")
    frontmatter = yaml.safe_load(pieces[1])
    if not isinstance(frontmatter, dict):
        raise CatalogBuildError(f"{path}: frontmatter must be a mapping")
    allowed_core_keys = {"schema", "kind", "title", "status", "updated", "source", "depends_on", "metadata"}
    unexpected_keys = sorted(set(frontmatter) - allowed_core_keys)
    if unexpected_keys:
        raise CatalogBuildError(f"{path}: unexpected frontmatter field(s): {', '.join(unexpected_keys)}")
    if frontmatter.get("schema") != "kb-entry@2":
        raise CatalogBuildError(f"{path}: expected schema kb-entry@2")
    kind = frontmatter.get("kind")
    if kind not in ENTRY_KINDS:
        raise CatalogBuildError(f"{path}: kind must be info or knowledge")
    title = frontmatter.get("title")
    status = frontmatter.get("status")
    updated = frontmatter.get("updated")
    if not isinstance(title, str) or not title.strip() or status not in ENTRY_STATUSES:
        raise CatalogBuildError(f"{path}: title and status must be valid core fields")
    if isinstance(updated, date):
        updated = updated.isoformat()
    if not isinstance(updated, str):
        raise CatalogBuildError(f"{path}: updated must be an ISO date string")
    try:
        date.fromisoformat(updated)
    except ValueError as error:
        raise CatalogBuildError(f"{path}: updated must be an ISO date string") from error
    provenance_key = "source" if kind == "info" else "depends_on"
    provenance = frontmatter.get(provenance_key)
    if not isinstance(provenance, list) or not provenance or any(not isinstance(item, str) or not item.strip() for item in provenance):
        raise CatalogBuildError(f"{path}: {provenance_key} must be a non-empty string list")
    metadata = frontmatter.get("metadata")
    if not isinstance(metadata, dict):
        raise CatalogBuildError(f"{path}: metadata must be a mapping")
    normalized_metadata: dict[str, list[str]] = {}
    for key, value in metadata.items():
        if key not in fields:
            raise CatalogBuildError(f"{path}: metadata field {key!r} is not declared")
        definition = fields[key]
        values = value if definition["multiple"] else [value]
        if definition["multiple"] and (not isinstance(values, list) or not values):
            raise CatalogBuildError(f"{path}: metadata field {key!r} must be a non-empty list")
        normalized_values = [_normalise(item, definition) for item in values]
        if any(item is None for item in normalized_values):
            raise CatalogBuildError(f"{path}: metadata field {key!r} does not match its schema")
        normalized_metadata[key] = [str(item) for item in normalized_values]
    for key, definition in fields.items():
        if kind in definition["required_for"] and key not in normalized_metadata:
            raise CatalogBuildError(f"{path}: required metadata field {key!r} is missing")
    for reference in provenance:
        if reference.startswith(("source/", "info/", "knowledge/")):
            candidate = (kb_root / reference.split("#", 1)[0]).resolve()
            try:
                candidate.relative_to(kb_root.resolve())
            except ValueError as error:
                raise CatalogBuildError(f"{path}: reference escapes package root: {reference}") from error
            if not candidate.is_file():
                raise CatalogBuildError(f"{path}: local reference does not exist: {reference}")
    body = pieces[2]
    frontmatter_lines = len(pieces[0].splitlines()) + len(pieces[1].splitlines()) + 2
    body_lines = [
        {"line": frontmatter_lines + index + 1, "text": line}
        for index, line in enumerate(body.splitlines())
    ]
    return {
        "package_name": package_name,
        "revision": revision,
        "entry_path": path.relative_to(kb_root).as_posix(),
        "kind": kind,
        "title": title.strip(),
        "status": status,
        "updated": updated,
        "body": body,
        "body_lines": body_lines,
        "source": provenance if kind == "info" else [],
        "depends_on": provenance if kind == "knowledge" else [],
        "metadata": normalized_metadata,
    }


def _validate_package(kb_root: Path, package_name: str, revision: str) -> tuple[dict[str, dict[str, Any]], str, str, list[dict[str, Any]], list[dict[str, str]]]:
    fields, schema_json, schema_sha256 = _load_schema(kb_root)
    entries: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for root_name in ("info", "knowledge"):
        root = kb_root / root_name
        if not root.exists():
            errors.append({"phase": "structure", "filePath": root_name, "field": root_name, "code": "DIRECTORY_MISSING", "message": "Content directory is required."})
            continue
        for path in sorted(root.rglob("*.md")):
            try:
                entries.append(_parse_entry(path, kb_root, fields, package_name, revision))
            except (CatalogBuildError, OSError, UnicodeError, yaml.YAMLError) as error:
                errors.append({"phase": "frontmatter", "filePath": path.relative_to(kb_root).as_posix(), "field": "metadata", "code": "INVALID_ENTRY", "message": str(error)})
    info_paths = {entry["entry_path"] for entry in entries if entry["kind"] == "info"}
    for entry in entries:
        for dependency in entry["depends_on"]:
            if dependency not in info_paths:
                errors.append({"phase": "references", "filePath": entry["entry_path"], "field": "depends_on", "code": "DEPENDENCY_NOT_FOUND", "message": f"Knowledge dependency does not resolve to an info entry: {dependency}"})
    for root_name in ("source", "info"):
        root = kb_root / root_name
        if not root.exists():
            continue
        for version in (path for path in root.rglob("*") if path.is_dir() and path.name.isdigit()):
            child_names = {child.name for child in version.iterdir()}
            if "shared" not in child_names and not any(ISO_COUNTRY_DIRECTORY.fullmatch(name) for name in child_names):
                continue
            invalid = sorted(name for name in child_names if name != "shared" and not ISO_COUNTRY_DIRECTORY.fullmatch(name))
            if invalid:
                errors.append({"phase": "structure", "filePath": version.relative_to(kb_root).as_posix(), "field": "layout", "code": "INVALID_VERSION_LAYOUT", "message": f"{version}: version directories may contain only shared/ or country-code directories; found {', '.join(invalid)}"})
    return fields, schema_json, schema_sha256, entries, errors


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        PRAGMA user_version = 2;
        CREATE TABLE packages (package_name TEXT PRIMARY KEY, revision TEXT NOT NULL);
        CREATE TABLE entries (id INTEGER PRIMARY KEY, package_name TEXT NOT NULL REFERENCES packages(package_name) ON DELETE CASCADE, entry_path TEXT NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('info', 'knowledge')), title TEXT NOT NULL, status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'deprecated', 'rejected')), updated TEXT NOT NULL, body TEXT NOT NULL, UNIQUE (package_name, entry_path));
        CREATE TABLE entry_lines (entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE, line_number INTEGER NOT NULL, text TEXT NOT NULL, PRIMARY KEY (entry_id, line_number));
        CREATE TABLE info_sources (entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE, position INTEGER NOT NULL, source TEXT NOT NULL, PRIMARY KEY (entry_id, position));
        CREATE TABLE knowledge_dependencies (entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE, position INTEGER NOT NULL, depends_on_entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE, PRIMARY KEY (entry_id, position));
        CREATE VIRTUAL TABLE entries_fts USING fts5(title, path_text, headings_text, body_text, tokenize = 'unicode61 remove_diacritics 2');
        CREATE TABLE package_schema (package_name TEXT PRIMARY KEY REFERENCES packages(package_name) ON DELETE CASCADE, schema_id TEXT NOT NULL CHECK (schema_id = 'kb-package-schema@2'), extends_id TEXT NOT NULL CHECK (extends_id = 'kb-core@2'), schema_sha256 TEXT NOT NULL CHECK (length(schema_sha256) = 64), schema_json TEXT NOT NULL CHECK (json_valid(schema_json)));
        CREATE TABLE field_definitions (id INTEGER PRIMARY KEY, package_name TEXT NOT NULL REFERENCES package_schema(package_name) ON DELETE CASCADE, field_key TEXT NOT NULL, origin TEXT NOT NULL CHECK (origin IN ('core', 'package')), field_type TEXT NOT NULL, multiple INTEGER NOT NULL CHECK (multiple IN (0, 1)), required_for_json TEXT NOT NULL CHECK (json_valid(required_for_json)), description TEXT NOT NULL, filterable INTEGER NOT NULL CHECK (filterable IN (0, 1)), search_enabled INTEGER NOT NULL CHECK (search_enabled IN (0, 1)), search_weight INTEGER, normalization TEXT NOT NULL, aliases_json TEXT NOT NULL CHECK (json_valid(aliases_json)), UNIQUE (package_name, field_key));
        CREATE TABLE entry_metadata_values (entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE, field_definition_id INTEGER NOT NULL REFERENCES field_definitions(id) ON DELETE CASCADE, field_key TEXT NOT NULL, position INTEGER NOT NULL, normalized_value TEXT NOT NULL, display_value TEXT NOT NULL, PRIMARY KEY (entry_id, field_definition_id, position));
        CREATE INDEX entry_metadata_values_filter_idx ON entry_metadata_values(field_key, normalized_value, entry_id);
        CREATE VIRTUAL TABLE metadata_fts USING fts5(field_key, value_text, tokenize = 'unicode61 remove_diacritics 2');
        """
    )


def _load_catalog(connection: sqlite3.Connection, package_name: str, revision: str, fields: dict[str, dict[str, Any]], schema_json: str, schema_sha256: str, entries: list[dict[str, Any]]) -> None:
    connection.execute("INSERT INTO packages (package_name, revision) VALUES (?, ?)", (package_name, revision))
    connection.execute("INSERT INTO package_schema (package_name, schema_id, extends_id, schema_sha256, schema_json) VALUES (?, 'kb-package-schema@2', 'kb-core@2', ?, ?)", (package_name, schema_sha256, schema_json))
    field_ids: dict[str, int] = {}
    definitions = {
        key: {
            "key": key,
            "type": field_type,
            "multiple": multiple,
            "required_for": required_for,
            "description": f"Platform core field: {key}.",
            "filterable": filterable,
            "search": {"enabled": searchable, **({"weight": 1000} if searchable else {})},
            "normalization": normalization,
            "aliases": {},
            "origin": "core",
        }
        for key, field_type, multiple, required_for, filterable, searchable, normalization in CORE_FIELDS
    }
    definitions.update({key: {**value, "origin": "package"} for key, value in fields.items()})
    for key in sorted(definitions):
        definition = definitions[key]
        cursor = connection.execute(
            "INSERT INTO field_definitions (package_name, field_key, origin, field_type, multiple, required_for_json, description, filterable, search_enabled, search_weight, normalization, aliases_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (package_name, key, definition["origin"], definition["type"], int(definition["multiple"]), _canonical_json(definition["required_for"]), definition["description"], int(definition["filterable"]), int(definition["search"]["enabled"]), definition["search"].get("weight"), definition["normalization"], _canonical_json(definition["aliases"])),
        )
        field_ids[key] = int(cursor.lastrowid)
    entry_ids: dict[str, int] = {}
    for entry in entries:
        cursor = connection.execute(
            "INSERT INTO entries (package_name, entry_path, kind, title, status, updated, body) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (package_name, entry["entry_path"], entry["kind"], entry["title"], entry["status"], entry["updated"], entry["body"]),
        )
        entry_id = int(cursor.lastrowid)
        entry_ids[entry["entry_path"]] = entry_id
        connection.executemany("INSERT INTO entry_lines (entry_id, line_number, text) VALUES (?, ?, ?)", [(entry_id, line["line"], line["text"]) for line in entry["body_lines"]])
        connection.executemany("INSERT INTO info_sources (entry_id, position, source) VALUES (?, ?, ?)", [(entry_id, position, source) for position, source in enumerate(entry["source"])])
        headings = " ".join(line["text"] for line in entry["body_lines"] if re.match(r"^#{1,6}\s+", line["text"]))
        connection.execute("INSERT INTO entries_fts (rowid, title, path_text, headings_text, body_text) VALUES (?, ?, ?, ?, ?)", (entry_id, entry["title"], entry["entry_path"], headings, entry["body"]))
        for key, values in entry["metadata"].items():
            for position, value in enumerate(values):
                connection.execute("INSERT INTO entry_metadata_values (entry_id, field_definition_id, field_key, position, normalized_value, display_value) VALUES (?, ?, ?, ?, ?, ?)", (entry_id, field_ids[key], key, position, value, value))
                connection.execute("INSERT INTO metadata_fts (field_key, value_text) VALUES (?, ?)", (key, value))
    for entry in entries:
        for position, dependency in enumerate(entry["depends_on"]):
            connection.execute("INSERT INTO knowledge_dependencies (entry_id, position, depends_on_entry_id) VALUES (?, ?, ?)", (entry_ids[entry["entry_path"]], position, entry_ids[dependency]))


def build_catalog(*, kb_root: Path, package_name: str, revision: str, out_dir: Path) -> dict[str, Any]:
    kb_root = kb_root.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = out_dir / "catalog.sqlite"
    catalog_path.unlink(missing_ok=True)
    fields, schema_json, schema_sha256, entries, errors = _validate_package(kb_root, package_name, revision)
    validation = {"ok": not errors, "errorCount": len(errors), "warningCount": 0, "entryCount": len(entries)}
    report = {"ok": not errors, "packageName": package_name, "revision": revision, "errors": errors, "warnings": []}
    (out_dir / "validation-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        (out_dir / "builder-metadata.json").write_text(json.dumps({"generator": {"name": "knowledge-package-catalog-builder", "version": "2"}, "validation": validation}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"validation": validation}
    connection = sqlite3.connect(catalog_path)
    try:
        _create_schema(connection)
        _load_catalog(connection, package_name, revision, fields, schema_json, schema_sha256, entries)
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise CatalogBuildError("catalog foreign-key check failed")
        connection.commit()
    except Exception:
        connection.close()
        catalog_path.unlink(missing_ok=True)
        raise
    connection.close()
    catalog = {"schema": "kb-catalog@2", "schemaSha256": schema_sha256}
    (out_dir / "builder-metadata.json").write_text(json.dumps({"generator": {"name": "knowledge-package-catalog-builder", "version": "2"}, "validation": validation, "catalog": catalog}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"catalogPath": str(catalog_path), "validation": validation, "catalog": catalog}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kb", type=Path, default=Path("."))
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = build_catalog(kb_root=args.kb, package_name=args.package_name, revision=args.revision, out_dir=args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validation"]["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
