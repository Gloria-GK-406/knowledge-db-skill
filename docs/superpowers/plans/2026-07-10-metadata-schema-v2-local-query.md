# Metadata Schema v2 Local Query Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Make the local CLI discover, validate, filter, and rank package-owned metadata fields declared in `kb-package-schema.json`.

**Architecture:** Replace fixed v1 frontmatter assumptions with explicit core validation plus a nested `metadata` map validated against the package schema. Use generic filters and field-weighted keyword scoring; do not special-case tags, countries, capabilities, or SAP.

**Tech Stack:** Python 3, argparse, unittest, Markdown/YAML frontmatter.

## Global Constraints

- No v1 behavior or `--tag` compatibility path.
- Core contract is `kb-core@2`; non-core fields are package-owned JSON definitions.
- Field weights are package data; matching algorithms and bounds are platform code.
- Repeated values within one filter are OR; different filter keys are AND.

---

### Task 1: Add schema parsing and v2 entry validation

**Files:**
- Modify: `skills/knowledge-db-maintain/scripts/kb.py`
- Modify: `tests/test_kb_cli.py`

- [ ] Write failing tests for a valid root `kb-package-schema.json`, nested metadata, invalid undeclared keys, invalid cardinality, missing info source, and missing knowledge dependency.
- [ ] Run those tests and confirm failure under the fixed v1 parser.
- [ ] Implement package-schema loading, core-profile validation, nested metadata parsing, declared type/cardinality validation, and actionable errors.
- [ ] Re-run the focused tests and confirm pass.

### Task 2: Expose schema discovery and generic filters

**Files:**
- Modify: `skills/knowledge-db-maintain/scripts/kb.py`
- Modify: `tests/test_kb_cli.py`

- [ ] Write failing tests for `kb schema`, `kb schema --json`, and `search --filter country=JP --filter capability=16T`.
- [ ] Run the tests and confirm failure because the command and filter grammar do not exist.
- [ ] Implement the schema command and repeatable generic `--filter key=value` parsing; validate field existence/filterability and apply OR-within/AND-across semantics to search and list.
- [ ] Re-run focused tests and confirm pass.

### Task 3: Implement field-weighted keyword search

**Files:**
- Modify: `skills/knowledge-db-maintain/scripts/kb.py`
- Modify: `tests/test_kb_cli.py`

- [ ] Write failing tests proving declared country/capability weights influence order, aliases such as `日本 -> JP` participate in keyword recall, and exact filters do not silently use aliases.
- [ ] Run those tests and confirm failure under the fixed title/tag/body scorer.
- [ ] Implement normalization, alias expansion, metadata match scoring, bounded platform coefficients, deterministic score tie-breaking, and empty-query-with-filter behavior.
- [ ] Re-run focused tests and the full `py -3 -m unittest tests.test_kb_cli -v` suite.

### Task 4: Validate a v2 package locally

**Files:**
- Modify: `tests/test_kb_cli.py`
- Optional create: `tests/fixtures/metadata-schema-v2/`

- [ ] Add an end-to-end fixture with shared 16T-style metadata and BR-only 2UP-style metadata.
- [ ] Run `kb schema`, `kb search`, `kb list`, `kb read --meta-only`, and `kb scan` against it through the CLI subprocess harness.
- [ ] Run the full suite, `git diff --check`, and commit the complete local v2 implementation.

## Verification

- `py -3 -m unittest tests.test_kb_cli -v`
- package fixture `kb scan`
- `git diff --check`
