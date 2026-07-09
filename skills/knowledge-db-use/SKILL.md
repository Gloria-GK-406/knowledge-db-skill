---
name: knowledge-db-use
description: Use when consuming a local Markdown knowledge base rooted directly in source, info, and knowledge folders, including finding entries, reading focused sections, searching titles/tags/body text, tracing provenance, and answering from grounded local knowledge without changing files.
---

# Knowledge DB Use

## Overview

Use this skill to read from a local Markdown knowledge base. Do not change files with this skill.

```text
source/      raw external material stored as files
info/        extracted information grounded in source
knowledge/   derived conclusions grounded in info
```

The grounding chain is `knowledge -> info -> source`. Prefer answering from `knowledge` when a suitable entry exists. Read supporting `info` before relying on a conclusion when accuracy matters.

Knowledge-base documents are expected to be written and maintained in English only. If entries contain non-English text, read them as available local evidence, but do not treat that as the desired authoring style.

Use `knowledge-db-maintain` instead when the task asks to initialize, add, update, delete, repair, or validate the knowledge base.

## Local Reading Workflow

1. Find the knowledge-base root: the directory that contains `source/`, `info/`, and `knowledge/`.
2. Browse likely entries with `tree`, `list`, `rg --files info knowledge`, or existing local CLI read-only commands if available.
3. Search with non-empty terms from the user request across `info/` and `knowledge/`.
4. Read focused entries before answering. For long files, read the relevant heading with section boundary context or a line window instead of loading everything.
5. Trace important knowledge claims back to their `depends_on` info entries; inspect source references when the answer depends on provenance.
6. Answer with the entry paths used and call out limits when supporting info is missing, stale-looking, or too narrow.

## Entry Format

Use file paths as stable IDs. Paths in metadata are relative to the knowledge-base root.

`info/**/*.md` entries use:

```yaml
---
schema: kb-info@1
kind: info
title: Display title
source:
  - source/example.pdf#page=3
  - https://example.com/docs/page
status: active
updated: 2026-07-07
tags:
  - example
---
```

`knowledge/**/*.md` entries use:

```yaml
---
schema: kb-knowledge@1
kind: knowledge
title: Display title
depends_on:
  - info/example.md
status: active
updated: 2026-07-07
tags:
  - example
---
```

Statuses are `draft`, `active`, `deprecated`, and `rejected`. Treat `active` as the default usable status; mention status when using draft, deprecated, or rejected entries.

## How To Search

- Start with `knowledge/` for conclusions, procedures, rules, recommendations, and reusable explanations.
- Search `info/` for extracted facts, source summaries, field mappings, catalogs, or evidence.
- Search by title, tag, domain term, acronym, and likely source name.
- Use non-empty search queries. Empty search is not browsing; use `tree` or `list` to browse.
- Search ranking prefers title exact or phrase matches, then tags, path/filename/slug, headings, and body matches.
- Hyphen, underscore, and space are treated as equivalent for tags and slugs, so `btp subaccount`, `btp-subaccount`, and `btp_subaccount` should find the same entry.
- Acronyms such as `CBC`, `BTP`, `XSUAA`, and `S/4HANA` are useful query terms and should be kept in the query.
- Status affects ranking: active entries are preferred over draft entries, while deprecated and rejected entries are pushed down.
- If several entries match, prefer the most specific active entry with the newest `updated` date after checking the ranked results.
- If no `knowledge` entry exists, synthesize only from relevant `info` entries and say that the answer is derived from info rather than an existing knowledge entry.

## How To Read

- Read frontmatter first to check `kind`, `status`, `updated`, `tags`, and grounding fields.
- For `knowledge`, read every listed `depends_on` info entry when the answer depends on the conclusion.
- For `info`, inspect `source` references when source identity or extraction reliability matters.
- Use Markdown headings to keep reads focused: `Scope`, `Facts`, and `Notes` for info; `Problem`, `Conclusion`, `Limits`, and `Reasoning` for knowledge.
- Use `read PATH --section Facts --context 1` when nearby section boundaries help orient the excerpt.
- Use `read PATH --line N --context M` for precise evidence around a line number.
- Use only one focused read mode at a time: `--meta-only`, `--body-only`, `--head N`, `--line N`, or `--section TEXT`. `--context` is allowed only with `--line` or `--section`.

## How To Trace

- Run `trace PATH` for a knowledge entry before relying on its conclusion; it shows `knowledge -> info -> source`.
- Run `trace PATH` for an info entry when you need to inspect its raw source references.
- If trace output points to missing or invalid dependencies, treat the entry as unreliable until maintained.

## Answering Rules

- Do not invent facts beyond the local entries.
- Do not cite raw source directly as support for a knowledge claim when a relevant `info` entry exists.
- Distinguish extracted facts from derived conclusions.
- Surface uncertainty from `Notes`, `Limits`, missing dependencies, old `updated` dates, or non-active statuses.
- If the user asks to change the knowledge base, switch to `knowledge-db-maintain`.
