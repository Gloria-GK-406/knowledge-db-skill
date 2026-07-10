"""Validate a kb-core@2 package without changing package data."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml


CONTENT_ROOTS = ("info", "knowledge")
LOCAL_REFERENCE_ROOTS = ("source/", "info/", "knowledge/")
ISO_COUNTRY_DIRECTORY = re.compile(r"^[A-Z]{2}$")
FIELD_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
CORE_FIELDS = {"schema", "kind", "title", "status", "updated", "source", "depends_on"}
SUPPORTED_NORMALIZERS = {"default", "keyword", "upper-case-code", "release-code"}
MAX_WEIGHT = 1000


class PackageCheckError(ValueError):
    """Raised when a package violates the package metadata contract."""


def _load_yaml(value: str, entry: Path) -> dict[str, Any]:
    parsed = yaml.safe_load(value)
    if not isinstance(parsed, dict):
        raise PackageCheckError(f"{entry}: frontmatter must be a mapping")
    return parsed


def _split_frontmatter(markdown: str, entry: Path) -> tuple[dict[str, Any], str]:
    if not markdown.startswith("---\n"):
        raise PackageCheckError(f"{entry}: missing YAML frontmatter")
    parts = markdown.split("---", 2)
    if len(parts) != 3:
        raise PackageCheckError(f"{entry}: unterminated YAML frontmatter")
    return _load_yaml(parts[1], entry), parts[2]


def _load_package_fields(kb_root: Path) -> dict[str, dict[str, Any]]:
    schema_path = kb_root / "kb-package-schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise PackageCheckError(f"missing package schema: {schema_path}") from error
    except json.JSONDecodeError as error:
        raise PackageCheckError(f"{schema_path}: invalid JSON: {error.msg}") from error
    if schema.get("schema") != "kb-package-schema@2" or schema.get("extends") != "kb-core@2":
        raise PackageCheckError(f"{schema_path}: expected kb-package-schema@2 extending kb-core@2")
    fields = schema.get("fields")
    if not isinstance(fields, dict):
        raise PackageCheckError(f"{schema_path}: fields must be a mapping")
    for name, definition in fields.items():
        if not isinstance(name, str) or not FIELD_KEY.fullmatch(name) or name in CORE_FIELDS or not isinstance(definition, dict):
            raise PackageCheckError(f"{schema_path}: each field must have a string name and mapping definition")
        if definition.get("type") != "string":
            raise PackageCheckError(f"{schema_path}: field {name!r} must have type 'string'")
        if not isinstance(definition.get("multiple"), bool):
            raise PackageCheckError(f"{schema_path}: field {name!r} must declare boolean multiple")
        if not isinstance(definition.get("description"), str) or not definition["description"].strip():
            raise PackageCheckError(f"{schema_path}: field {name!r} must have a description")
        if not isinstance(definition.get("filterable"), bool):
            raise PackageCheckError(f"{schema_path}: field {name!r} must declare boolean filterable")
        search = definition.get("search")
        if not isinstance(search, dict) or not isinstance(search.get("enabled"), bool):
            raise PackageCheckError(f"{schema_path}: field {name!r} must declare search.enabled")
        weight = search.get("weight")
        if not isinstance(weight, int) or isinstance(weight, bool) or not 0 <= weight <= MAX_WEIGHT:
            raise PackageCheckError(f"{schema_path}: field {name!r} must declare integer search.weight from 0 to {MAX_WEIGHT}")
        if not search["enabled"] and weight != 0:
            raise PackageCheckError(f"{schema_path}: field {name!r} cannot have a weight when search is disabled")
        normalization = definition.get("normalization", "default")
        if normalization not in SUPPORTED_NORMALIZERS:
            raise PackageCheckError(f"{schema_path}: field {name!r} has unsupported normalization")
        aliases = definition.get("aliases", {})
        if not isinstance(aliases, dict) or not all(
            isinstance(key, str) and key.strip() and isinstance(values, list)
            and all(isinstance(value, str) and value.strip() for value in values)
            for key, values in aliases.items()
        ):
            raise PackageCheckError(f"{schema_path}: field {name!r} aliases must map strings to string lists")
    return fields


def _validate_core(entry: Path, frontmatter: Mapping[str, Any]) -> None:
    allowed = {"schema", "kind", "title", "status", "updated", "source", "depends_on", "metadata"}
    unexpected = sorted(set(frontmatter) - allowed)
    if unexpected:
        raise PackageCheckError(f"{entry}: unexpected frontmatter field(s): {', '.join(unexpected)}")
    if frontmatter.get("schema") != "kb-entry@2":
        raise PackageCheckError(f"{entry}: expected schema 'kb-entry@2'")
    for required in ("kind", "title", "status", "updated"):
        if not frontmatter.get(required):
            raise PackageCheckError(f"{entry}: missing required core field {required!r}")
    kind = frontmatter["kind"]
    if kind not in {"info", "knowledge"}:
        raise PackageCheckError(f"{entry}: kind must be 'info' or 'knowledge'")
    provenance_field = "source" if kind == "info" else "depends_on"
    provenance = frontmatter.get(provenance_field)
    if not isinstance(provenance, list) or not provenance or not all(isinstance(value, str) for value in provenance):
        raise PackageCheckError(f"{entry}: {kind} entry requires non-empty {provenance_field!r} string list")
    metadata = frontmatter.get("metadata")
    if not isinstance(metadata, Mapping):
        raise PackageCheckError(f"{entry}: v2 entry requires metadata mapping")


def _validate_metadata(entry: Path, metadata: Mapping[str, Any], fields: Mapping[str, Mapping[str, Any]]) -> None:
    for field_name, value in metadata.items():
        definition = fields.get(field_name)
        if not isinstance(definition, Mapping):
            raise PackageCheckError(f"{entry}: metadata field {field_name!r} is not declared")
        if definition["multiple"] is True:
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise PackageCheckError(f"{entry}: metadata field {field_name!r} must be a list of strings")
        elif not isinstance(value, str):
            raise PackageCheckError(f"{entry}: metadata field {field_name!r} must be a string")


def _validate_local_references(entry: Path, kb_root: Path, frontmatter: Mapping[str, Any]) -> None:
    provenance_field = "source" if frontmatter["kind"] == "info" else "depends_on"
    for reference in frontmatter[provenance_field]:
        if not reference.startswith(LOCAL_REFERENCE_ROOTS):
            continue
        package_path = reference.split("#", 1)[0]
        candidate = (kb_root / package_path).resolve()
        try:
            candidate.relative_to(kb_root.resolve())
        except ValueError as error:
            raise PackageCheckError(f"{entry}: local reference escapes package root: {reference}") from error
        if not candidate.is_file():
            raise PackageCheckError(f"{entry}: local reference does not exist: {reference}")


def _validate_version_layout(kb_root: Path) -> None:
    for root_name in ("info", "source"):
        root = kb_root / root_name
        if not root.exists():
            continue
        for version in (path for path in root.rglob("*") if path.is_dir() and path.name.isdigit()):
            children = tuple(version.iterdir())
            child_names = {child.name for child in children}
            if "shared" not in child_names and not any(ISO_COUNTRY_DIRECTORY.fullmatch(name) for name in child_names):
                continue
            invalid = [child.name for child in children if child.name != "shared" and not ISO_COUNTRY_DIRECTORY.fullmatch(child.name)]
            if invalid:
                joined = ", ".join(sorted(invalid))
                raise PackageCheckError(
                    f"{version}: version directories may contain only shared/ or country-code directories; found {joined}"
                )


def check_package(kb_root: Path) -> int:
    fields = _load_package_fields(kb_root)
    errors: list[str] = []
    for root_name in CONTENT_ROOTS:
        root = kb_root / root_name
        if not root.exists():
            continue
        for entry in sorted(root.rglob("*.md")):
            try:
                frontmatter, _ = _split_frontmatter(entry.read_text(encoding="utf-8"), entry)
                _validate_core(entry, frontmatter)
                _validate_metadata(entry, frontmatter["metadata"], fields)
                _validate_local_references(entry, kb_root, frontmatter)
            except (OSError, UnicodeError, yaml.YAMLError, PackageCheckError) as error:
                errors.append(str(error))
    try:
        _validate_version_layout(kb_root)
    except PackageCheckError as error:
        errors.append(str(error))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2
    print(f"OK: package validation passed for {kb_root}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kb", type=Path, default=Path("."), help="knowledge package root (default: current directory)")
    args = parser.parse_args(argv)
    try:
        return check_package(args.kb.resolve())
    except PackageCheckError as error:
        print(error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
