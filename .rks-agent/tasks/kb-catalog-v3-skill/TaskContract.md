---
schema_version: "0.1"
kind: rks-task-contract
id: kb-catalog-v3-skill
revision: 1
status: ready
intake_mode: interactive
parent_contract: null
depends_on: []
contributes_to: []
---

# TaskContract: Define and scaffold the breaking kb-catalog@3 package contract

## Source Request

Update the local knowledge-db skill first so new and maintained packages use the breaking v3 catalog contract with required package name/description metadata and filterable-field facet generation.

## Background

The maintain skill's package skeleton and documentation currently prescribe kb-catalog@2. Two real knowledge packages will be upgraded from the new template, and knowledge-service will consume only v3 artifacts.

## Goal

knowledge-db-maintain documents, scaffolds, validates, and tests one authoritative kb-catalog@3 producer contract.

## Scope

### In

- Define required root package metadata for non-empty name and description.
- Upgrade package skeleton scripts, CI template/docs, smoke checks, and tests from v2 to v3.
- Require facet materialization for filterable metadata fields.
- Update maintain-skill guidance and generated-package file expectations.

### Out

- Updating installed global skill copies.
- Modifying either real knowledge package or knowledge-service directly.
- Supporting v2 templates or compatibility-generation mode.
- Commit, push, publish, or register the skill without separate confirmation.

## Constraints

- The skill remains lightweight and package-local; it must not add service dependencies to producer CI.
- The v3 contract must define exact package descriptor validation, artifact versions, required SQLite schema, and deterministic facet semantics.
- Generated skeleton validation must fail closed for missing/invalid required package metadata.

## Success Conditions

- SC-1: Skill documentation clearly specifies the required v3 package descriptor and artifact contract.
- SC-2: A newly initialized package includes all required v3 metadata, scripts, CI, and tests.
- SC-3: Skeleton builder emits a v3 catalog with package name/description and filterable-field facets.
- SC-4: Skeleton smoke/tests reject v2 or incomplete v3 contracts and pass valid v3 cases.
- SC-5: Skill repository validation and relevant test suite pass.

## Required Evidence

- SC-1: Documentation and asset assertions.
- SC-2: CLI/init regression test over a generated package.
- SC-3: SQLite schema/query assertions from skeleton builder tests.
- SC-4: Negative/positive smoke and metadata tests.
- SC-5: Fresh skill validation and test output.

## Authorization

### Allowed

- Create task artifacts and a controlled worktree.
- Modify skill documentation, skeleton assets, scripts, CI templates, and tests.
- Run local validation and tests.

### Requires Confirmation

- Commit, push, publish, register, or update installed global skill copies.

## Assumptions

- The two producer repositories will intentionally adopt the resulting v3 contract without v2 compatibility.

## Open Questions

- None.
