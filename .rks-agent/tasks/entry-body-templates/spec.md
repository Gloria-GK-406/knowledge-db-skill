# Specification: Canonical entry body templates

## Purpose

Define one lightweight, domain-neutral body contract for each kb-core@2 entry kind and make that contract visible in the maintenance skill, available as package scaffolding, and enforceable by package validation.

## Canonical bodies

Every entry body begins with exactly one level-one ATX heading whose text equals the trimmed `title` frontmatter value.

An `info` entry then contains exactly these level-two ATX headings in this order:

1. `Scope`
2. `Facts`
3. `Notes`

A `knowledge` entry then contains exactly these level-two ATX headings in this order:

1. `Problem and Context`
2. `Conclusion`
3. `Limits`
4. `Reasoning`

Additional level-three and lower headings are allowed within a canonical section. Heading-like text inside fenced code blocks is ignored. Additional, missing, duplicated, or reordered level-one or level-two headings make the entry invalid.

The sections have these semantics:

- `Scope`: state coverage, applicability, and explicit exclusions.
- `Facts`: record only objective statements supported by `source`; organize details with lower-level headings when useful.
- `Notes`: record source positioning, extraction method, conflicts, uncertainty, and limitations.
- `Problem and Context`: state the reusable problem, applicability, and prerequisites.
- `Conclusion`: state the derived guidance, recommendation, or decision rule.
- `Limits`: state non-applicability, risks, version constraints, and unknowns.
- `Reasoning`: explain how the declared `depends_on` info supports the conclusion without introducing unsupported facts.

## Package templates

`kb init` materializes domain-neutral templates at `templates/info.md` and `templates/knowledge.md`. Each contains valid core frontmatter placeholders, the canonical body headings, and concise Markdown comments that guide authors without becoming asserted package content.

Re-running `kb init` preserves the existing byte-identity rule: an unchanged template is accepted and a modified template is reported as a conflict rather than overwritten.

## Entry creation interface

The CLI exposes:

```text
kb new info <relative-path> --title <title> --source <reference> [--source <reference> ...] [--status <status>]
kb new knowledge <relative-path> --title <title> --depends-on <info-path> [--depends-on <info-path> ...] [--status <status>]
```

Behavior:

- `<relative-path>` is relative to the selected `info/` or `knowledge/` root, must end in `.md`, and must not be absolute or contain `..`.
- `--status` defaults to `draft`; `updated` is the current local ISO date.
- The command renders the matching package template and creates missing parent directories.
- The command requires at least one provenance argument appropriate to the kind and rejects the other kind's provenance option through its command grammar.
- The command refuses to overwrite any existing filesystem object.
- The command fails when the package template is missing, modified so required placeholders are absent, or cannot render exactly once per placeholder.
- The rendered entry has valid core frontmatter and canonical body structure. Package-specific required metadata remains an author responsibility and may require editing before full package validation succeeds.

## Validation behavior

The generated package checker and catalog producer apply the canonical body contract to every `info/**/*.md` and `knowledge/**/*.md` entry. A body violation is reported against the entry as an invalid entry with a diagnostic that identifies the title or section problem.

The maintenance CLI applies the same body rules when deciding whether an entry is valid for `list`, `search`, `read`, and `trace`, so invalid entries cannot appear valid merely because the caller did not run `scan` first.

## Compatibility

- Existing entries without canonical sections become invalid when checked by the revised skill or a newly initialized/generated checker. This is intentional because the user requested a constrained template contract.
- Existing source storage, frontmatter fields, metadata schemas, query behavior, provenance rules, and artifact schema remain unchanged.
- Existing packages are not rewritten automatically.

## Acceptance conditions

- AC-1: Skill instructions show both canonical bodies and explain every section.
- AC-2: `kb init` materializes both templates and retains conflict safety.
- AC-3: `kb new` creates both entry kinds, handles repeated provenance, uses draft/current date defaults, and refuses unsafe paths or overwrite.
- AC-4: Validation accepts canonical bodies, lower-level subsections, and heading-like fenced-code content.
- AC-5: Validation rejects title mismatch, additional/missing/duplicate/reordered H1/H2 headings.
- AC-6: Repository tests and skill validation pass.
