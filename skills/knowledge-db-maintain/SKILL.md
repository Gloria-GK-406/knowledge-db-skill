---
name: knowledge-db-maintain
description: Use when maintaining a local Markdown knowledge base rooted directly in source, info, and knowledge folders, including initializing, adding source material, creating info or knowledge entries, updating entries, deleting entries, validating, tracing, impact analysis, and stale checks.
---

# Knowledge DB Maintain

## Overview

Use this skill to change a local Markdown knowledge base whose root contains `source/`, `info/`, and `knowledge/` directly.

```text
source/      raw external material stored as files
info/        extracted information grounded in source
knowledge/   derived conclusions grounded in info
```

Keep the grounding chain strict: `knowledge -> info -> source`. Create missing `info` before writing `knowledge`; do not cite raw source directly from a knowledge entry.

Use `knowledge-db-use` instead when the task is only to find, read, search, or answer from existing knowledge.

## Management Rules

- Write and maintain knowledge-base documents in English. This applies to `info/**/*.md`, `knowledge/**/*.md`, titles, headings, tags, notes, and derived conclusions.
- If the knowledge base is inside a Git repository, make knowledge-base edits in an independent worktree. Create or switch to the worktree before changing `source/`, `info/`, or `knowledge/`.
- At the end of a Git-backed maintenance task, ask the user how to finish. Offer these choices:
  1. Commit, push to the remote, and create a PR or MR if possible.
  2. Merge the work into the main branch.
  3. Do nothing.
- Do not choose the finish option for the user.

## CLI

The bundled CLI lives in `scripts/kb.py`. Run it from the knowledge-base root, or pass `--kb PATH` to target another root.

```bash
python scripts/kb.py <command>
python scripts/kb.py --kb /path/to/knowledge-base <command>
```

PowerShell:

```powershell
.\scripts\kb.ps1 <command>
.\scripts\kb.ps1 --kb C:\path\to\knowledge-base <command>
```

sh/bash:

```bash
sh scripts/kb.sh <command>
```

Set `KB_PYTHON` when a wrapper should use a specific Python interpreter.

## Entry Format

Use file paths as stable IDs. Paths in metadata are relative to the knowledge-base root.

`info/**/*.md` frontmatter:

```yaml
---
schema: kb-info@1
kind: info
title: Display title
source:
  - source/sap/example.pdf#page=3
  - https://example.com/docs/page
status: draft
updated: 2026-07-07
tags:
  - sap
  - btp
---
```

`knowledge/**/*.md` frontmatter:

```yaml
---
schema: kb-knowledge@1
kind: knowledge
title: Display title
depends_on:
  - info/sap/example.md
status: draft
updated: 2026-07-07
tags:
  - sap
  - btp
---
```

Allowed statuses are `draft`, `active`, `deprecated`, and `rejected`. Do not add extra frontmatter fields. Put explanation, notes, limits, and derivation in the Markdown body.

Write every `tags`, `source`, and `depends_on` item as a YAML string. Quote tag values that YAML could parse as numbers, booleans, or nulls, especially SAP scope item codes and numeric IDs such as `"1e1"`, `"1e3"`, `"4e9"`, `"287"`, `"637"`, and `"649"`. Unquoted values like `1e1` may be parsed as the number `10` and will fail validation.

## Commands

| Command | Purpose |
|---|---|
| `init` | Create `source/`, `info/`, and `knowledge/` in the target root. |
| `new-info PATH --title TITLE --source SOURCE --tag TAG` | Create an `info` entry with valid metadata and a body scaffold. |
| `new-knowledge PATH --title TITLE --depends-on INFO --tag TAG` | Create a `knowledge` entry with valid metadata and a body scaffold. |
| `tree [PATH] --files --titles` | Browse directories and Markdown titles. |
| `list [info|knowledge]` | List entries, optionally filtering by `--tag` or `--status`. |
| `search QUERY` | Search entries with weighted title, tag, path, heading, and body matching. |
| `read PATH` | Read full content or focused slices. |
| `scan` / `validate` | Validate structure, metadata, source references, and dependencies. |
| `trace PATH` | Show `knowledge -> info -> source` or `info -> source`. |
| `impact PATH` | Find entries affected by a changed source or info path. |
| `stale` | Find knowledge whose info dependencies are newer. |

Useful read options for checking entries before or after edits:

| Option | Meaning |
|---|---|
| `--meta-only` | Print only YAML frontmatter. |
| `--body-only` | Print only the Markdown body. |
| `--head N` | Print only the first N lines. |
| `--line N --context M` | Print a line window with file line numbers. |
| `--section TEXT --context N` | Print the Markdown section whose heading contains text, optionally with nearby section boundary context. |

Use only one focused read mode at a time: `--meta-only`, `--body-only`, `--head N`, `--line N`, or `--section TEXT`. `--context` is allowed only with `--line` or `--section`.

Useful search options:

| Option | Meaning |
|---|---|
| `--kind info|knowledge` | Limit search by layer. |
| `--tag TAG` | Require a tag. |
| `--all a,b` | Require all listed terms. |
| `--any a,b` | Require at least one listed term. |
| `--context N` | Show N file lines around matches. |

Search behavior:

- Empty search queries are not supported. Use `list` or `tree` for browsing.
- Ranking prefers title exact or phrase matches, then tags, path/filename/slug, headings, and body matches.
- Hyphen, underscore, and space are equivalent for tags and slugs.
- English search normalizes lowercase, hyphen/underscore splits, and simple camel-case boundaries. Chinese text remains searchable, with lightweight n-gram support for longer runs.
- Acronym tokens such as `CBC`, `BTP`, `XSUAA`, and `S/4HANA` remain useful query terms.
- Status influences order: `active` ranks above `draft`, while `deprecated` and `rejected` rank lower.
- When `--kind` is omitted, the command searches both `info` and `knowledge`; do not assume one layer is hidden.

## Workflows

### Initialize A Knowledge Base

1. Run `init` from the target repository root.
2. Put file-based raw material under `source/`.
3. Use URLs directly in `info.source` when the source is a web page.
4. Run `tree --files --titles` to inspect the structure.

### Add Source Material

1. Put file-based raw material under `source/`.
2. Preserve original filenames when useful; normalize only when names are unsafe or unclear.
3. Do not rewrite raw source to make extraction easier. If a cleaned representation is needed, create it as an `info` entry.
4. Use web URLs directly in `info.source` when the source is not a local file.

### Turn Source Into Info

1. Inspect the raw file or URL.
2. Choose an `info` granularity by topic, source section, or reusable fact group.
3. Run `new-info`, repeating `--source` and `--tag` as needed.
4. Fill `Scope`, `Facts`, and `Notes`.
5. Run `scan`.

### Turn Info Into Knowledge

1. Locate relevant info with `tree`, `list`, or `search`.
2. Read the info entries before deriving conclusions; prefer `read PATH --section Facts --context 1` or a line window for long entries.
3. Run `new-knowledge`, repeating `--depends-on` and `--tag` as needed.
4. Fill `Problem`, `Conclusion`, `Limits`, and `Reasoning`.
5. Run `trace` and then `scan`.

### Update Existing Entries

1. Use `trace` to inspect grounding before editing.
2. Use `impact SOURCE_OR_INFO_PATH` after source or info changes.
3. Use `stale` to find knowledge that may need review.
4. Search with specific non-empty terms; browse with `tree` or `list` instead of empty search.
5. Edit Markdown normally.
6. Update the `updated` date when the entry meaning, sources, dependencies, or status changes.
7. Preserve the required frontmatter shape and keep paths relative to the knowledge-base root.
8. Run `trace` for changed knowledge entries, then run `scan`.

### Delete Entries Or Source

1. Run `impact PATH` before deleting a source or info entry.
2. If deleting an `info` entry, update or delete every `knowledge` entry that depends on it.
3. If deleting source material, update or delete every `info` entry whose `source` references it.
4. If deleting a `knowledge` entry, remove only that Markdown file unless other user instructions require broader cleanup.
5. Delete files with normal filesystem tools only after the dependency impact is understood.
6. Run `scan`; no deleted path should remain in `source` or `depends_on` metadata.

## Validation Rules

`scan` and `validate` report hard errors for invalid structure or broken grounding:

- Missing root directories: `source/`, `info/`, or `knowledge/`.
- Missing or extra frontmatter fields.
- Invalid `schema`, `kind`, `status`, or `updated`.
- Empty `source`, `depends_on`, or `tags`, or non-string items in those lists.
- Local `info.source` outside `source/` or pointing to a missing file.
- `knowledge.depends_on` pointing to a URL, `source/`, `knowledge/`, outside `info/`, or a missing info entry.

Warnings identify maintainability issues, such as missing recommended body sections or unreachable web sources. Fix hard errors first.
