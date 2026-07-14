---
schema_version: "0.1"
kind: rks-task-contract
id: entry-body-templates
revision: 1
status: ready
intake_mode: interactive
parent_contract: null
depends_on: []
contributes_to: []
---

# TaskContract: Constrain info and knowledge entry templates

## Source Request

Modify the knowledge-db skill so that info and knowledge entries use explicit, consistent body templates based on the established SAP-BTP-knowledge-db info pattern.

## Background

The current skill defines frontmatter, provenance, and layer semantics, but it does not provide or validate body templates. The reference SAP package consistently uses `Scope`, `Facts`, and `Notes` for info entries, while the knowledge layer should preserve the agreed problem/context, conclusion, limits, and reasoning order.

## Goal

Make the entry body contract discoverable, scaffolded, and mechanically validated for new kb-core@2 packages.

## Scope

### In

- Document canonical info and knowledge body structures in `knowledge-db-maintain`.
- Bundle reusable info and knowledge template assets.
- Add a CLI creation command that materializes either template with valid core frontmatter.
- Extend the generated package checker to validate required top-level title and ordered required sections.
- Add regression tests for scaffolding and validation behavior.
- Reconcile registered capability metadata if the published capability changes.

### Out

- Rewrite existing knowledge-base package entries.
- Modify the SAP-BTP-knowledge-db repository.
- Enforce domain-specific subsections below the canonical second-level headings.
- Publish, push, merge, or open a pull request without separate authorization.

## Constraints

- Preserve the strict `knowledge -> info -> source` provenance chain.
- Keep templates domain-neutral and lightweight.
- Permit additional third-level and lower headings inside canonical sections.
- Reject missing, duplicated, or out-of-order canonical second-level sections.
- Work in an isolated Git worktree and preserve unrelated user changes.

## Success Conditions

- SC-1: The maintain skill explicitly defines canonical info and knowledge body templates and their semantics.
- SC-2: The CLI can create valid info and knowledge entries from bundled templates without overwriting existing files.
- SC-3: The package checker accepts canonical bodies and rejects missing, duplicated, or out-of-order canonical sections.
- SC-4: Automated tests cover both entry kinds, creation safety, and body validation failure modes.
- SC-5: Skill validation and the relevant repository test suite pass.

## Required Evidence

- SC-1: Diff and skill validator output.
- SC-2: CLI regression test output and generated-file assertions.
- SC-3: Package-checker regression test output.
- SC-4: Test names and passing suite output.
- SC-5: Fresh validation and full test command output.

## Authorization

### Allowed

- Create task artifacts and an isolated worktree.
- Modify skill documentation, bundled assets, scripts, tests, and affected registration metadata.
- Run local validation and tests.

### Requires Confirmation

- Commit, push, merge, publish, or open a pull request.
- Modify any external repository or installed global skill copy.

## Assumptions

- Canonical info order is `Scope`, `Facts`, `Notes`.
- Canonical knowledge order is `Problem and Context`, `Conclusion`, `Limits`, `Reasoning`.
- A single H1 matching the frontmatter title is part of the body contract.

## Open Questions

- None.
