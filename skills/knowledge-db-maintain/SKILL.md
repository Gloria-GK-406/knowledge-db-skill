---
name: knowledge-db-maintain
description: Maintain a kb-core@2 local Markdown knowledge base, including package-defined metadata validation, generic metadata filtering, provenance tracing, and metadata-aware search.
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
      "search": { "enabled": true, "weight": 700 },
      "aliases": { "JP": ["Japan", "日本"] }
    }
  }
}
```

`type` is `string`, `number`, or `boolean`; `multiple` selects an array versus single value. Package authors choose a field description, exact-filter availability, keyword-search availability, a bounded `0..1000` keyword weight, and optional field-scoped aliases. Do not put business fields such as country or capability in directories or top-level frontmatter.

```yaml
---
schema: kb-core@2
kind: info
title: Intercompany Processing
status: active
updated: 2026-07-10
source:
  - source/sap/16T.md
metadata:
  country:
    - JP
    - DE
  capability:
    - 16T
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
