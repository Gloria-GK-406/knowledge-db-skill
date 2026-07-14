---
name: knowledge-db-organize
description: Use when reorganizing a local Markdown knowledge base whose info, knowledge, or source entries are mixed together; when sibling folders express incompatible concepts; or when scattered files and subfolders must be merged into a normalized hierarchy with one consistent abstraction per directory depth (such as product, version, then capability), while preserving provenance and links.
---

# Knowledge DB Organize

Organize the filesystem layout of a knowledge base. Preserve entry content and its semantic metadata; folders exist for maintenance boundaries, not as the authority for filtering or search.

## Workflow

1. Discover the package root and read its `kb-package-schema.json`, `README.md`, and existing layout rules. Identify `source/`, `info/`, and `knowledge/` roots and whether package validation constrains version directories.
2. Inventory entries and folders at each affected depth. For every sibling directory, label its current abstraction: product/domain, version, capability, entry grouping, or unknown. Do not infer a dimension from a name alone when the files disagree.
3. Define one hierarchy contract before moving anything. Assign exactly one abstraction to every affected depth, such as `layer 1 = product`, `layer 2 = version`, `layer 3 = capability`. A depth must never mix dimensions: if one sibling is a version, every sibling at that depth must be a version.
4. Build a migration map from every old path to a new path. Merge entries from multiple old folders into the same new folder whenever they share the dimensions assigned to that depth. Resolve name collisions explicitly; do not silently overwrite, deduplicate, or discard entries.
5. Present the hierarchy contract and migration map when the requested restructuring leaves meaningful choices unresolved. Otherwise, perform the requested moves. Create only directories that implement the contract; remove an empty old directory only after its contents have been migrated.
6. Update all moved-path references: `source`, `depends_on`, Markdown links, catalog inputs, and package-local scripts or documentation that contain the old relative paths. Do not alter factual content or metadata values merely to match a directory name.
7. Run the package's validation (`kb scan` or `kb validate`, and any package-provided checker). Search for stale old paths. Report the final hierarchy, merged groups, moved paths, and any ambiguous entries left untouched.

## Hierarchy Rules

- Keep the `source/`, `info/`, and `knowledge/` roots distinct. Never merge entries across those layers merely because their names are similar.
- Choose dimensions from the actual corpus and package contract. Typical order is broad-to-narrow: product/domain -> version -> capability -> entry group. Do not introduce unnecessary levels for a one-item branch.
- Treat versions as peer values only: do not place `v1` beside `payments` at the same depth. Likewise, do not mix a capability folder with a date, owner, or status folder at one depth.
- Use directory names as stable maintenance labels. Keep query, filtering, aliases, ranking, and applicability semantics in frontmatter and `kb-package-schema.json`, even when a directory is named after a capability or version.
- Preserve the grounding chain `knowledge -> info -> source`. Moving a file requires repairing every affected reference before considering the migration complete.
- Keep the operation reversible: retain a complete migration map in the task result, and do not delete non-empty folders or unreferenced-looking entries without explicit user authorization.

## Decision Examples

| Mixed layout | Normalized layout |
| --- | --- |
| `info/payments/v1/`, `info/orders/returns/`, `info/payments/refunds/` | Choose `domain -> version -> capability`; migrate to `info/payments/v1/refunds/` and `info/orders/v1/returns/` only after confirming the applicable versions. |
| `knowledge/v1/`, `knowledge/v2/`, `knowledge/auth/` | Do not move blindly: this depth mixes version and capability. Choose a contract such as `knowledge/<version>/<capability>/`, then merge `auth/` entries under their applicable versions. |

## Completion Criteria

Finish only when every affected depth has one declared abstraction, every moved reference resolves, no stale paths remain, and package validation passes. If an entry belongs to multiple versions or capabilities, retain its metadata and either place it in the shared grouping defined by the contract or request a placement decision; do not duplicate it without an explicit duplication policy.
