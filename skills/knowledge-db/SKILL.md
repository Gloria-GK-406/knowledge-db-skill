---
name: knowledge-db
description: Use when working with a local Markdown knowledge base organized into source, info, and knowledge layers, including creating, reading, searching, tracing, and validating entries with bundled scripts.
---

# Knowledge DB

## 1. What This System Is

Use this skill to work with a local Markdown knowledge base rooted at `.kb/`. The system separates raw material, extracted information, and derived knowledge into three layers:

```text
.kb/
  source/      raw external material stored as files
  info/        organized information extracted from source
  knowledge/   derived knowledge based on info
```

Keep the layer boundary strict:

- Put external files or raw captures under `source/`, or reference a web page directly with an `http://` or `https://` URL in info metadata.
- Create `info` when content extracts, cleans, groups, or summarizes source material.
- Create `knowledge` when content makes a conclusion, procedure, rule, recommendation, or reusable explanation from one or more info files.
- Treat dependent `knowledge` as suspect when an `info` entry is wrong or outdated.

Use file paths as stable IDs. Do not invent a separate ID scheme unless the user asks for one.

Knowledge should be grounded through `knowledge -> info -> source`. Prefer creating missing `info` before writing `knowledge`; do not cite raw source directly from a knowledge entry when an info layer should exist.

## 2. What It Includes

The bundled CLI logic lives in `scripts/kb.py`. Use the launcher that fits the current shell; all launchers accept the same commands and options.

```bash
python scripts/kb.py <command>
```

From PowerShell:

```powershell
.\scripts\kb.ps1 <command>
```

Prefer `kb.ps1` on Windows when entries may contain Chinese or other non-ASCII text; it forces PowerShell and the Python child process to use UTF-8 output.

From sh/bash:

```bash
sh scripts/kb.sh <command>
```

If `python` resolves to the wrong interpreter, set `KB_PYTHON` before running the wrapper:

```powershell
$env:KB_PYTHON = "C:\path\to\python.exe"
.\scripts\kb.ps1 <command>
```

```bash
KB_PYTHON=/path/to/python sh scripts/kb.sh <command>
```

If using this skill from its installed folder, the launchers are beside this `SKILL.md` under `scripts/`.

All commands support:

| Option | Meaning |
|---|---|
| `--kb PATH` | Knowledge base root. Defaults to `.kb`. It may appear before the command, after the command, or between command options. Use this when the database is outside the current working directory. |

### Creation and Reading Commands

| Command | Purpose |
|---|---|
| `init` | Create `.kb/source`, `.kb/info`, and `.kb/knowledge`. |
| `new-info PATH --title TITLE --source SOURCE` | Create an info Markdown file. |
| `new-knowledge PATH --title TITLE --depends-on INFO` | Create a knowledge Markdown file. |
| `read PATH` | Print a Markdown entry. |

Use `new-info` when the target entry belongs under `.kb/info/`.

| Option | Meaning |
|---|---|
| `--source SOURCE` | Repeatable. Local source path or web URL. Local paths may use a locator after `#`; web URLs may include query strings and fragments. |
| `--tag TAG` | Repeatable metadata tag. |
| `--body TEXT` | Write Markdown body at creation time. |
| `--body-file FILE` | Read Markdown body from a UTF-8 file. |
| `--body-stdin` | Read Markdown body from stdin. |
| `--force` | Overwrite an existing entry. |

Use `new-knowledge` when the target entry belongs under `.kb/knowledge/`.

| Option | Meaning |
|---|---|
| `--depends-on INFO` | Repeatable. Add one supporting info dependency each time. |
| `--tag TAG` | Repeatable metadata tag. |
| `--status STATUS` | Defaults to `draft`. |
| `--body TEXT` / `--body-file FILE` / `--body-stdin` | Write Markdown body at creation time. |
| `--force` | Overwrite an existing entry. |

Use `read` to inspect an entry before relying on it or updating it.

| Option | Meaning |
|---|---|
| `--meta-only` | Print only YAML frontmatter. |
| `--body-only` | Print only Markdown body. |
| `--head N` | Print only the first N lines. |

### Browsing and Search Commands

| Command | Purpose |
|---|---|
| `tree [PATH]` | Print a folder tree. |
| `list [info|knowledge]` | List entries. |
| `search [QUERY]` | Search title, tags, and body without an index. |

| Command | Options |
|---|---|
| `tree` | `--files`, `--titles`, `--depth N` |
| `list` | `--tag TAG`, `--status STATUS`, `--quiet` |
| `search` | `--kind info|knowledge`, `--tag TAG`, `--all a,b`, `--any a,b`, `--context N`, `--title-only` |

Use `tree --files --titles` when you need to scan the knowledge base by path and title before opening files.

Use `search --context N` when keyword matches need surrounding lines. Use `--all a,b` for terms that must all appear, and `--any a,b` for acceptable alternatives.

### Validation and Trace Commands

| Command | Purpose |
|---|---|
| `scan` | Validate metadata, local source paths, web source accessibility, and knowledge dependencies. |
| `trace PATH` | Show `knowledge -> info -> source`, or `info -> source`. |
| `impact PATH` | Find info/knowledge affected by an info or source path. |
| `stale` | Find knowledge whose info dependencies are newer than the knowledge. |

Run `scan` after creating or editing entries. It checks local source files for existence, web sources for reachability, and `knowledge.depends_on` paths for missing info dependencies. Use `scan --web-timeout N` to adjust URL check timeout seconds. Use `trace` before relying on a knowledge entry. Use `impact` when source or info changes; source may be a local source path or web URL. Use `stale` to find knowledge that may need review.

## 3. When and How To Use It

### Starting or Repairing a Knowledge Base

Use this when the `.kb/` structure is missing, incomplete, or being set up for the first time.

1. Run `init`.
2. Put raw external material under `.kb/source/`, or keep a web page as an exact URL source reference.
3. Create organized facts or summaries with `new-info`.
4. Create derived conclusions or procedures with `new-knowledge` only after the supporting info exists.
5. Run `scan` and fix reported metadata, path, or dependency problems.

### Turning Source Into Info

Use this when the user provides or points to raw material such as a spreadsheet, PDF, document, web export, log, transcript, or notes.

1. Copy or place file-based raw material under `.kb/source/`; for web pages, keep the exact URL as the source.
2. Inspect the source with appropriate tools.
3. Choose info granularity by topic, source section, or reusable fact group.
4. Create each info entry with `new-info`.
5. Pass exact local source paths or web URLs through repeatable `--source`; include locators or URL fragments when useful.
6. Run `scan`.
7. Use `tree info --files --titles` to review what was created.

### Turning Info Into Knowledge

Use this when the user asks for a conclusion, procedure, rule, summary, or reusable understanding.

1. Find relevant info with `tree`, `list`, or `search`.
2. Read the info entries.
3. Derive the knowledge from those info entries. If source material is needed but no info entry exists, create info first.
4. Create the knowledge with `new-knowledge`.
5. Repeat `--depends-on INFO` for every supporting info file.
6. In the body, separate conclusion, reasoning, usage guidance, and limits when those parts are relevant.
7. Run `trace PATH` to confirm the dependency chain, then run `scan`.

### Reviewing or Maintaining Existing Knowledge

Use this when the user asks whether a knowledge entry is still grounded, what changes if an info/source changes, or where a conclusion came from.

1. Use `read` or `tree --files --titles` to locate the entry.
2. Use `trace` to inspect its info and source chain.
3. Use `impact PATH` from changed source or info paths to find affected entries.
4. Use `stale` to find knowledge whose dependencies are newer.
5. Update Markdown content with normal editing tools when needed.
6. Run `scan` after changes.

### Choosing Between Info and Knowledge

Use this decision before creating new entries:

- Create `info` for extracted, cleaned, grouped, or summarized source material.
- Create `knowledge` for judgments, recommendations, procedures, explanations, or synthesis across info entries.
- When unsure, create `info` first.
- Treat knowledge without explicit `depends_on` as ungrounded in this system.
