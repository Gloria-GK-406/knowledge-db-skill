# Maintain Skill Package Skeleton v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Make `knowledge-db-maintain` initialize and validate the reusable v2 package skeleton.

**Architecture:** Bundle generic package scripts and CI as Skill assets. Extend the maintain CLI to copy those assets idempotently and delegate scan/validate to the generated package checker, while retaining its metadata-aware query commands.

**Tech Stack:** Python 3, Node.js asset files, JSON, YAML, unittest.

## Global Constraints

- No v1 compatibility path.
- New package fields are string-only and require `multiple`, `filterable`, `description`, and `search` with an integer weight.
- `kb init` never overwrites differing user files.
- Paths are maintenance structure, never query/filter/score semantics.
- Do not change `knowledge-db-use` or `knowledge-service`.

---

### Task 1: Add generic package skeleton assets and test initialization

**Files:**
- Create: `skills/knowledge-db-maintain/assets/package-skeleton/**`
- Modify: `skills/knowledge-db-maintain/scripts/kb.py`
- Modify: `tests/test_kb_cli.py`

- [ ] Write failing tests that run `kb init` in an empty directory and assert every skeleton asset exists, is generic, and the generated checker passes.
- [ ] Add a failing test that changes a generated file, reruns init, and asserts init refuses to overwrite it.
- [ ] Bundle the generic schema, scripts/catalog helpers, checker, and workflow as maintain-Skill assets.
- [ ] Implement idempotent asset materialization and strict conflict reporting in `cmd_init`.
- [ ] Run focused initialization tests and commit.

### Task 2: Align v2 validation behavior with generated package scripts

**Files:**
- Modify: `skills/knowledge-db-maintain/scripts/kb.py`
- Modify: `skills/knowledge-db-maintain/SKILL.md`
- Modify: `tests/test_kb_cli.py`

- [ ] Write failing tests that prove scan/validate delegate to the generated checker and propagate invalid schema/layout/reference diagnostics.
- [ ] Tighten package-field schema validation to the string-only, fully declared package contract.
- [ ] Keep schema/search/filter/alias behavior path-independent and verify the SAP package works through the Skill.
- [ ] Update maintain Skill instructions for skeleton initialization, checker authority, and service builder boundary.
- [ ] Run full unit suite plus real SAP package schema/search/scan checks and commit.
