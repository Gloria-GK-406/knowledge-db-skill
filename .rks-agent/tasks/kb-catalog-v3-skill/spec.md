# Specification: kb-catalog@3 package producer contract

## Purpose

Define the required package-local producer contract consumed by the v3 knowledge service. This is a breaking catalog-artifact upgrade; v2 generation and compatibility behavior are out of scope.

## Package descriptor

Every package root must contain `kb-package.json`:

```json
{
  "schema": "kb-package@1",
  "name": "Human-readable knowledge base name",
  "description": "Non-empty agent-facing purpose and coverage description."
}
```

The descriptor is package-level metadata. It does not change `kb-package-schema@2`, entry frontmatter, package-defined field rules, provenance, or filter semantics. The checker and builder reject a missing descriptor, an unsupported schema, unknown top-level properties, or blank/non-string name or description.

## v3 artifact

The builder emits `kb-catalog@3` and SQLite `user_version = 3`. The catalog contains exactly one package row with:

- `package_name`: stable machine identifier supplied to the builder;
- `name`: descriptor name;
- `description`: descriptor description;
- `revision`: supplied source revision.

The existing entry, provenance, schema, field-definition, metadata-value, and FTS relations remain semantically unchanged.

The catalog adds `field_value_facets` with one row per filterable field and normalized value currently represented by at least one entry. Each row contains the package name, field key, normalized value, a deterministic display value, and the count of distinct matching entries. The table has a primary key and an index that support package-and-field value paging. Non-filterable fields never produce facets.

Facet rows are derived while compiling the already-validated in-memory entries or immediately from the same SQLite transaction; they require no second Markdown scan. Counts must equal the distinct-entry aggregation over `entry_metadata_values`.

## Artifact metadata and validation

The generated builder metadata uses `kb-catalog@3`; the immutable manifest uses `kb-catalog-artifact@3`; and the latest pointer uses `kb-catalog-latest@3`. Their catalog schema values must be `kb-catalog@3`.

The smoke checker requires the v3 SQLite version, package metadata columns, facet table/index, expected v3 artifact metadata, and facet parity with entry metadata. It rejects v2 identifiers and incomplete v3 structure.

## Skeleton and documentation

`kb init` materializes `kb-package.json` plus the revised package scripts, workflow, tests, templates, and schema. Rerun safety treats the new descriptor as a managed skeleton asset. `knowledge-db-maintain` documents the descriptor, the v3 producer contract, and the distinction between current filterable values and a manually governed vocabulary.

## Acceptance mapping

- SC-1: descriptor positive/negative tests and generated-package assertions.
- SC-2 and SC-3: builder and SQLite smoke tests assert v3 identity, package columns, facets, and parity.
- SC-4: metadata writer/workflow tests assert all v3 identifiers.
- SC-5: the relevant skill CLI and skeleton producer suites pass.
