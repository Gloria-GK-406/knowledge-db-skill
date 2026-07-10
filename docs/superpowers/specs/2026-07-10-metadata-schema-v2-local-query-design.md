# Metadata Schema v2 Local Query Design

## Status

Proposed. This specification covers the `knowledge-db-skill` CLI and validation behavior only. It does not implement online-service code or package migration.

## Goal

Extend the local knowledge-base skill so that it can discover a package's searchable metadata fields, validate package-owned metadata, and execute generic keyword and exact-filter queries with the same semantic contract as the catalog artifact.

This is a clean v2 cutover. The local skill does not preserve v1 metadata validation or v1 query behavior.

## Architecture Impact

No architecture-intent document covers this repository footprint. Architecture documentation will be bootstrapped from landed code; this specification is the design-time intent.

## Input Contract

The knowledge-base root must contain:

```text
kb-package-schema.json
source/
info/
knowledge/
```

The package schema explicitly extends `kb-core@2`. Core frontmatter is mandatory, while all package-owned values are stored under a nested `metadata` map. The CLI must parse nested mappings and arrays rather than the current limited flat-frontmatter subset.

The CLI must reject:

- a missing or invalid package schema;
- an unsupported core-profile version;
- undeclared metadata keys;
- values with the wrong type or cardinality;
- missing metadata fields declared as required for an entry kind;
- invalid weights, alias definitions, or normalization declarations;
- missing core `source` for info or `depends_on` for knowledge.

## Discoverability

Add a read-only command that exposes the merged core and package field contract before callers construct filters.

```text
kb schema
kb schema --json
```

Each field result includes key, description, type, cardinality, requiredness, filterability, searchability, keyword weight, normalization, and aliases where present. The human output must clearly identify core versus package-owned fields.

## Generic Search Interface

Retain free-text search and add repeatable generic metadata filters.

```text
kb search "intercompany process" --filter country=JP
kb search 16T --filter country=JP --filter capability=16T
kb search "日本" --kind info
```

Rules:

- All fields marked `search.enabled=true` participate in keyword recall.
- A package field contributes `field_weight * platform_match_coefficient` to the result score.
- The platform owns exact, phrase, and token coefficients; packages choose only bounded field weights.
- Repeated values for one field use OR semantics; filters across different fields use AND semantics.
- Filters use normalized exact values. Aliases help keyword recall but do not silently change exact-filter meaning.
- Empty text is allowed only when at least one filter is supplied.
- Results are sorted by final score, then stable path tie-breakers.

The existing fixed tag option is replaced by generic `--filter`. `tags`, if declared by the package, are ordinary metadata fields rather than special CLI behavior.

## Ranking and Normalization

The skill retains platform-owned normalization for case, hyphen, underscore, whitespace, camel-case boundaries, CJK terms, and SAP identifiers. Package field definitions select an allowed normalizer and supply field-scoped aliases.

The ranking implementation must separately calculate core-field and metadata-field contributions so that metadata weights are observable in tests. It must not create query syntax or ranking rules special to `country`, `capability`, or SAP.

## Validation and Read Behavior

- `scan` and `validate` validate the v2 package schema and all metadata values.
- `list` accepts generic filters using the same `--filter` grammar.
- `read --meta-only` returns core metadata plus the validated metadata map.
- `trace` continues to use core `source` and `depends_on` roles; package metadata never replaces provenance.

## Conformance Corpus

The local skill and `knowledge-service` must pass a shared, versioned conformance corpus containing:

- schema-valid and schema-invalid packages;
- single- and multi-value fields;
- field-weight ranking assertions;
- exact filters and alias keyword queries;
- CJK country aliases such as `日本 -> JP`;
- SAP identifiers such as `16T` and `2UP`;
- shared-content and country-specialized entries;
- unknown-field, invalid-type, missing-core, empty-query, and tie-break failures.

The corpus defines expected entry order and score components. The Python CLI and TypeScript service may have separate implementations, but they must satisfy the same corpus.

## Acceptance Criteria

- `kb schema` reliably tells an agent which fields are searchable and filterable.
- A package-defined field can be added without modifying CLI query syntax.
- Keyword queries search declared metadata and apply declared field weights.
- Generic exact filters work for any declared filterable field.
- Validation, search, list, read, and trace use the same merged core-plus-package contract.
- All behavior is covered by the shared conformance corpus and local CLI tests.

## Out of Scope

- Service SQLite implementation, artifact synchronization, and HTTP/MCP route implementation.
- Compatibility with the existing fixed frontmatter model or fixed `--tag` interface.
