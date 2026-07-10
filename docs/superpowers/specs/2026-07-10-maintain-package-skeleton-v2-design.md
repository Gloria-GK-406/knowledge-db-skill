# Maintain Skill Package Skeleton v2 Design

## Status

Approved for implementation from the SAP knowledge-package scripts contract.

## Goal

Extend `knowledge-db-maintain` so `kb init` creates a complete, self-validating knowledge package instead of only three content directories and an empty schema. The generated package must match the scripts and CI contract proven in `SAP-BTP-knowledge-db`.

## Bidirectional Contract Reconciliation

The package contract provides `kb-package-schema.json`, `scripts/check_package.py`, `scripts/catalog/`, and `.github/workflows/catalog-artifact.yml`. The Skill already provides v2 schema discovery, generic metadata filters, field weights, aliases, and path-independent search.

The previous Skill schema validator accepted number/boolean fields and optional field-definition properties, whereas the package checker accepts only string fields and requires `multiple`, `filterable`, `description`, and `search` including a non-negative integer weight. New packages use the stricter package contract. `kb scan` and `kb validate` execute the package-local checker so the user-visible validation result is authoritative and cannot drift from CI.

## Generated Skeleton

`kb init` creates missing directories and non-overwriting files:

```text
kb-package-schema.json
source/.gitkeep
info/.gitkeep
knowledge/.gitkeep
scripts/README.md
scripts/check_package.py
scripts/catalog/__init__.py
scripts/catalog/build_catalog_from_service.mjs
scripts/catalog/metadata.py
scripts/catalog/sqlite_smoke.py
scripts/catalog/write_artifact_metadata.py
.github/workflows/catalog-artifact.yml
```

Assets are generic: no SAP entries, country fields, credentials, or service implementation are embedded. The workflow delegates catalog construction to the configured `knowledge-service` repository. Re-running `kb init` is idempotent and refuses to overwrite an existing differing skeleton file.

## Command Contract

- `kb init`: generate or verify the complete skeleton, then run the generated checker.
- `kb scan` / `kb validate`: invoke `<package>/scripts/check_package.py --kb <package>` using the current Python interpreter and propagate its diagnostics and exit code.
- `kb schema`, `list`, `search`, `read`, and `trace`: retain their existing v2 metadata behavior. They do not derive search semantics from `shared` or country directory names.

## Out of Scope

- Changing `knowledge-db-use`.
- Implementing the v2 catalog builder in `knowledge-service`.
- Supporting v1 packages or packages without the generated scripts skeleton.

## Architecture Impact

No architecture-intent document covers this Skill footprint. Architecture documentation will be bootstrapped from landed code before a merge decision.
