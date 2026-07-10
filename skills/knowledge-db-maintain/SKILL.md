---
name: knowledge-db-maintain
description: Use when maintaining a kb-core@2 local Markdown knowledge base with package-defined metadata, self-contained artifact validation, generic filters, provenance tracing, or metadata-aware search.
---

# Knowledge DB Maintain

Use this skill to change a local knowledge base that contains `source/`, `info/`, `knowledge/`, and `kb-package-schema.json`. Keep its grounding chain strict: `knowledge -> info -> source`.

## V2 Package Contract

Every package extends `kb-core@2` in its root `kb-package-schema.json`. Core frontmatter fields are `schema`, `kind`, `title`, `status`, and `updated`; `info` also requires `source`, while `knowledge` requires `depends_on`. Package-specific values may appear only under the nested `metadata` mapping.

```json
{
  "schema": "kb-package-schema@2",
  "extends": "kb-core@2",
  "fields": {
    "country": {
      "type": "string",
      "multiple": true,
      "description": "Countries where this entry applies.",
      "filterable": true,
      "normalization": "upper-case-code",
      "search": { "enabled": true, "weight": 700 },
      "aliases": { "JP": ["Japan", "日本"] }
    }
  }
}
```

Package fields use `string`, `integer`, `number`, `boolean`, or `date`. Every definition
explicitly declares its type, `multiple`, a non-empty `description`, `filterable`, compatible
`normalization`, and `search.enabled`. Searchable fields use an integer `search.weight` from
`1..1000`; disabled search fields omit `weight`. `multiple` selects an array versus single
value. Aliases are allowed only for searchable string fields. Do not put business fields such
as country or capability in directories or top-level frontmatter.

```yaml
---
schema: kb-entry@2
kind: info
title: Intercompany Processing
status: active
updated: '2026-07-10'
source:
  - source/sap/"16T".md
metadata:
  country:
    - JP
    - DE
  capability:
    - "16T"
---
```

## Commands

Run `kb schema` before constructing a query; `kb schema --json` returns the complete merged core-plus-package contract. Use generic filters, never a field-specific switch:

```text
kb scan
kb search "intercompany" --filter country=JP
kb search --filter country=JP --filter country=DE --filter capability=16T
kb list info --filter country=BR
kb read info/sap/16T.md --meta-only
kb trace knowledge/sap/intercompany.md
```

Repeated values of one `--filter` key are OR; different keys are AND. Filters are normalized exact values. Aliases increase keyword recall only, never exact-filter matches. An empty search is permitted only with at least one filter. Search ranks declared metadata fields using their package-owned weights; paths and folder names do not supply metadata semantics.

Use `scan` or `validate` after all changes. It rejects a missing/invalid schema, undeclared fields, bad cardinality or types, missing required package fields, missing `source`/`depends_on`, and invalid provenance references.

`scan` and `validate` delegate to the package-owned `scripts/check_package.py --kb <root>`
created by `kb init`; that generated checker is the authority for package validation and
version-directory layout. It returns the checker exit code and diagnostics unchanged. Keep
directories for maintenance organization only: queries, filters, aliases, scoring, and
validation semantics come from frontmatter and `kb-package-schema.json`, never a path.

## Initialize a Package

Run `kb init` in an empty package root to materialize the generic schema, empty
`source/`, `info/`, and `knowledge/` roots, package checker, catalog helpers, and artifact
workflow. It is safe to rerun only while generated assets remain byte-identical; it refuses
to overwrite changed files or directory collisions. The generated Python producer validates
the package and builds `kb-catalog@2` SQLite locally; its CI needs only package-local scripts,
PyYAML, and the repository's MinIO publication secrets. It never checks out or imports a
query service. A service consumes the published artifact and validates its generic v2 contract.
