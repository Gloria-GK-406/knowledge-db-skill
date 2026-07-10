---
name: knowledge-db-use
description: Consume a kb-core@2 local Markdown knowledge base by discovering package metadata, searching with weighted generic fields, reading entries, and tracing provenance without modifying files.
---

# Knowledge DB Use

Use this skill read-only for packages that contain `source/`, `info/`, `knowledge/`, and `kb-package-schema.json`. The evidence chain is `knowledge -> info -> source`.

Start every unfamiliar package with `kb schema` (or `kb schema --json`). It exposes the core contract plus package-owned metadata fields, their descriptions, cardinality, filterability, keyword-search status, weights, normalization, and aliases.

Use generic filters declared by that package:

```text
kb search "intercompany" --filter country=JP
kb list info --filter capability=16T
kb search --filter country=JP --filter country=DE
kb read info/sap/16T.md --meta-only
kb trace knowledge/sap/intercompany.md
```

Repeated filters on a key are OR; filters on different keys are AND. Keyword search uses only core searchable content and fields whose package schema enables search. A field's package-owned weight increases its keyword score. Field aliases help keyword recall but do not alter exact filters. Do not infer country, capability, or another business field from a file path: read `metadata` and the schema.

Read frontmatter before relying on an entry. `info` must trace to `source`; `knowledge` must trace to `info`. Surface status and provenance limits in any answer.
