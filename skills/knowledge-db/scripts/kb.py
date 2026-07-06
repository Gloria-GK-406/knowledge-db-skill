#!/usr/bin/env python3
import argparse
import re
import sys
from datetime import date
from pathlib import Path


KB_DIRS = ("source", "info", "knowledge")
REQUIRED = {
    "info": ("kind", "title", "source", "created", "updated", "tags"),
    "knowledge": ("kind", "title", "depends_on", "created", "updated", "tags", "status"),
}


def today():
    return date.today().isoformat()


def kb_root(args):
    return Path(args.kb).resolve()


def rel_posix(path):
    return path.as_posix()


def normalize_md_path(kind, value):
    raw = Path(value.replace("\\", "/"))
    parts = raw.parts
    if parts and parts[0] == kind:
        raw = Path(*parts[1:])
    if raw.suffix != ".md":
        raw = raw.with_suffix(".md")
    if raw.is_absolute() or ".." in raw.parts:
        raise SystemExit("Entry path must be relative and stay inside the knowledge base.")
    return raw


def split_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1 :])
    return None, text


def compose_frontmatter(metadata):
    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def parse_scalar(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_simple_yaml(yaml_text):
    data = {}
    current_key = None
    for raw in yaml_text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith("  - ") and current_key:
            data.setdefault(current_key, []).append(parse_scalar(raw[4:]))
            continue
        if raw.startswith("- ") and current_key:
            data.setdefault(current_key, []).append(parse_scalar(raw[2:]))
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?$", raw)
        if not match:
            raise ValueError(f"Unsupported YAML line: {raw}")
        key, value = match.group(1), match.group(2) or ""
        if value == "":
            data[key] = []
            current_key = key
        else:
            data[key] = parse_scalar(value)
            current_key = key
    return data


def read_entry(path):
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8-sig")
    yaml_text, body = split_frontmatter(text)
    if yaml_text is None:
        return {}, body, "missing YAML frontmatter"
    try:
        return parse_simple_yaml(yaml_text), body, None
    except ValueError as exc:
        return {}, body, str(exc)


def write_entry(path, metadata, heading, body=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if body is None:
        body = f"# {heading}\n\n"
    path.write_text(f"{compose_frontmatter(metadata)}\n\n{body.rstrip()}\n", encoding="utf-8")


def iter_entries(root, kind=None):
    kinds = [kind] if kind in ("info", "knowledge") else ["info", "knowledge"]
    for entry_kind in kinds:
        base = root / entry_kind
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.md")):
            yield entry_kind, path


def resolve_kb_rel(root, value):
    value = value.replace("\\", "/")
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path


def resolve_existing_path(root, value):
    path = resolve_kb_rel(root, value)
    if path.exists():
        return path
    if path.suffix != ".md":
        md_path = path.with_suffix(".md")
        if md_path.exists():
            return md_path
    return path


def display_path(root, path):
    try:
        return rel_posix(path.relative_to(root))
    except ValueError:
        return str(path)


def read_body_arg(args):
    body_values = [args.body is not None, args.body_file is not None, args.body_stdin]
    if sum(1 for present in body_values if present) > 1:
        raise SystemExit("Use only one of --body, --body-file, or --body-stdin.")
    if args.body is not None:
        return args.body
    if args.body_file is not None:
        return Path(args.body_file).read_text(encoding="utf-8")
    if args.body_stdin:
        return sys.stdin.read()
    return None


def cmd_init(args):
    root = kb_root(args)
    for name in KB_DIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    print(f"Initialized {root}")
    return 0


def cmd_new_info(args):
    root = kb_root(args)
    path = root / "info" / normalize_md_path("info", args.path)
    if path.exists() and not args.force:
        print(f"Refusing to overwrite existing file: {display_path(root, path)}", file=sys.stderr)
        return 2
    metadata = {
        "kind": "info",
        "title": args.title,
        "source": args.source,
        "created": today(),
        "updated": today(),
        "tags": args.tag or [],
    }
    write_entry(path, metadata, args.title, read_body_arg(args))
    print(display_path(root, path))
    return 0


def cmd_new_knowledge(args):
    root = kb_root(args)
    path = root / "knowledge" / normalize_md_path("knowledge", args.path)
    if path.exists() and not args.force:
        print(f"Refusing to overwrite existing file: {display_path(root, path)}", file=sys.stderr)
        return 2
    metadata = {
        "kind": "knowledge",
        "title": args.title,
        "depends_on": args.depends_on or [],
        "created": today(),
        "updated": today(),
        "tags": args.tag or [],
        "status": args.status,
    }
    write_entry(path, metadata, args.title, read_body_arg(args))
    print(display_path(root, path))
    return 0


def has_tag(data, wanted):
    if not wanted:
        return True
    tags = data.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    return all(tag in tags for tag in wanted)


def cmd_list(args):
    root = kb_root(args)
    count = 0
    for kind, path in iter_entries(root, args.kind):
        data, _body, error = read_entry(path)
        if error:
            continue
        if args.status and data.get("status") != args.status:
            continue
        if not has_tag(data, args.tag):
            continue
        count += 1
        title = data.get("title", "(untitled)")
        status = f" [{data.get('status')}]" if data.get("status") else ""
        print(f"{display_path(root, path)} - {title}{status}")
    if count == 0 and not args.quiet:
        print("No entries found.")
    return 0


def cmd_tree(args):
    root = kb_root(args)
    target = root if args.path in (None, ".", "") else resolve_kb_rel(root, args.path)
    if not target.exists():
        print(f"Path not found: {display_path(root, target)}", file=sys.stderr)
        return 2
    if target.is_file():
        print(display_path(root, target))
        return 0
    print_tree(root, target, args.files or args.titles, args.titles, args.depth)
    return 0


def print_tree(root, target, include_files, include_titles, max_depth):
    label = display_path(root, target) or "."
    print(f"{label}/")

    def visit(directory, prefix, depth):
        if max_depth is not None and depth >= max_depth:
            return
        children = []
        for child in sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if child.name.startswith(".") and child.name != ".kb":
                continue
            if child.is_dir():
                children.append(child)
            elif include_files and child.suffix == ".md":
                children.append(child)
        for index, child in enumerate(children):
            last = index == len(children) - 1
            branch = "`-- " if last else "|-- "
            next_prefix = "    " if last else "|   "
            suffix = "/" if child.is_dir() else ""
            title = ""
            if include_titles and child.is_file():
                data, _body, _error = read_entry(child)
                if data.get("title"):
                    title = f" - {data['title']}"
            print(f"{prefix}{branch}{child.name}{suffix}{title}")
            if child.is_dir():
                visit(child, prefix + next_prefix, depth + 1)

    visit(target, "", 0)


def cmd_read(args):
    root = kb_root(args)
    path = resolve_existing_path(root, args.path)
    if not path.exists() or not path.is_file():
        print(f"Path not found: {display_path(root, path)}", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8")
    yaml_text, body = split_frontmatter(text)
    if args.meta_only and args.body_only:
        print("Use only one of --meta-only or --body-only.", file=sys.stderr)
        return 2
    if args.meta_only:
        output = f"---\n{yaml_text or ''}\n---\n"
    elif args.body_only:
        output = body
    else:
        output = text
    lines = output.splitlines()
    if args.head is not None:
        lines = lines[: args.head]
    print("\n".join(lines))
    return 0


def split_terms(values):
    terms = []
    for value in values or []:
        for part in value.split(","):
            term = part.strip()
            if term:
                terms.append(term)
    return terms


def search_text_for_context(text, terms, context):
    if context <= 0 or not terms:
        return []
    lowered_terms = [term.lower() for term in terms]
    lines = text.splitlines()
    wanted = set()
    for index, line in enumerate(lines):
        low = line.lower()
        if any(term in low for term in lowered_terms):
            start = max(0, index - context)
            end = min(len(lines), index + context + 1)
            wanted.update(range(start, end))
    snippets = []
    last = None
    for index in sorted(wanted):
        if last is not None and index > last + 1:
            snippets.append("  ...")
        snippets.append(f"  {index + 1}: {lines[index]}")
        last = index
    return snippets


def cmd_search(args):
    root = kb_root(args)
    all_terms = split_terms(args.all_terms)
    any_terms = split_terms(args.any_terms)
    if args.query:
        all_terms.insert(0, args.query)
    if not all_terms and not any_terms and not args.tag:
        print("Provide a query, --all/--any term, or --tag filter.", file=sys.stderr)
        return 2
    all_terms_low = [term.lower() for term in all_terms]
    any_terms_low = [term.lower() for term in any_terms]
    matches = 0
    for kind, path in iter_entries(root, args.kind):
        data, body, error = read_entry(path)
        if error:
            continue
        if not has_tag(data, args.tag):
            continue
        haystack_parts = [data.get("title", ""), " ".join(data.get("tags", []))]
        if not args.title_only:
            haystack_parts.append(body)
        haystack = "\n".join(haystack_parts).lower()
        all_match = all(term in haystack for term in all_terms_low)
        any_match = True if not any_terms_low else any(term in haystack for term in any_terms_low)
        if all_match and any_match:
            matches += 1
            print(f"{display_path(root, path)} - {data.get('title', '(untitled)')}")
            context_text = "\n".join(haystack_parts)
            for snippet in search_text_for_context(context_text, all_terms + any_terms, args.context):
                print(snippet)
    if matches == 0:
        print("No matches.")
    return 0


def source_exists(root, source):
    base = source.split("#", 1)[0]
    return (root / base).exists()


def cmd_scan(args):
    root = kb_root(args)
    problems = []
    for dirname in KB_DIRS:
        if not (root / dirname).is_dir():
            problems.append(("ERROR", f"missing directory: {dirname}/"))

    for kind, path in iter_entries(root):
        rel = display_path(root, path)
        data, _body, error = read_entry(path)
        if error:
            problems.append(("ERROR", f"{rel}: {error}"))
            continue
        if data.get("kind") != kind:
            problems.append(("ERROR", f"{rel}: kind should be {kind!r}"))
        for key in REQUIRED[kind]:
            if key not in data or data[key] in ("", []):
                problems.append(("WARN", f"{rel}: missing {key}"))
        if kind == "info":
            sources = data.get("source", [])
            if isinstance(sources, str):
                sources = [sources]
            for source in sources:
                if not source_exists(root, source):
                    problems.append(("WARN", f"{rel}: source not found: {source}"))
        if kind == "knowledge":
            deps = data.get("depends_on", [])
            if isinstance(deps, str):
                deps = [deps]
            for dep in deps:
                if not resolve_kb_rel(root, dep).exists():
                    problems.append(("ERROR", f"{rel}: missing dependency: {dep}"))

    if problems:
        for level, message in problems:
            print(f"{level}: {message}")
        return 1 if any(level == "ERROR" for level, _ in problems) else 0
    print("OK")
    return 0


def entry_title(path):
    if not path.exists():
        return "(missing)"
    data, _body, error = read_entry(path)
    if error:
        return "(invalid)"
    return data.get("title", "(untitled)")


def list_value(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def cmd_trace(args):
    root = kb_root(args)
    path = resolve_existing_path(root, args.path)
    if not path.exists():
        print(f"Path not found: {display_path(root, path)}", file=sys.stderr)
        return 2
    data, _body, error = read_entry(path)
    if error:
        print(f"{display_path(root, path)}: {error}", file=sys.stderr)
        return 1
    rel = display_path(root, path)
    print(f"{rel} - {data.get('title', '(untitled)')}")
    kind = data.get("kind")
    if kind == "knowledge":
        deps = list_value(data.get("depends_on"))
        if not deps:
            print("  (no dependencies)")
        for dep in deps:
            dep_path = resolve_existing_path(root, dep)
            print(f"  -> {display_path(root, dep_path)} - {entry_title(dep_path)}")
            if dep_path.exists():
                dep_data, _dep_body, dep_error = read_entry(dep_path)
                if not dep_error:
                    for source in list_value(dep_data.get("source")):
                        print(f"     -> {source}")
    elif kind == "info":
        sources = list_value(data.get("source"))
        if not sources:
            print("  (no sources)")
        for source in sources:
            print(f"  -> {source}")
    else:
        print(f"  (unsupported kind: {kind})")
    return 0


def info_entries_for_source(root, source_target):
    target_base = source_target.split("#", 1)[0].replace("\\", "/")
    matches = []
    for _kind, path in iter_entries(root, "info"):
        data, _body, error = read_entry(path)
        if error:
            continue
        for source in list_value(data.get("source")):
            source_base = source.split("#", 1)[0].replace("\\", "/")
            if source_base == target_base:
                matches.append(path)
                break
    return matches


def knowledge_entries_for_info(root, info_rel_paths):
    normalized = {value.replace("\\", "/") for value in info_rel_paths}
    matches = []
    for _kind, path in iter_entries(root, "knowledge"):
        data, _body, error = read_entry(path)
        if error:
            continue
        deps = {dep.replace("\\", "/") for dep in list_value(data.get("depends_on"))}
        if deps & normalized:
            matches.append(path)
    return matches


def cmd_impact(args):
    root = kb_root(args)
    target = args.path.replace("\\", "/")
    target_path = resolve_existing_path(root, target)
    affected_info = []
    affected_knowledge = []
    if target.startswith("source/"):
        affected_info = info_entries_for_source(root, target)
        info_rels = [display_path(root, path) for path in affected_info]
        affected_knowledge = knowledge_entries_for_info(root, info_rels)
    elif target.startswith("info/") or (target_path.exists() and "info" in target_path.parts):
        if target_path.exists():
            affected_info = [target_path]
        info_rel = display_path(root, target_path)
        affected_knowledge = knowledge_entries_for_info(root, [info_rel])
    else:
        print("Impact target must be an info path or source path.", file=sys.stderr)
        return 2

    if affected_info:
        print("info:")
        for path in affected_info:
            print(f"  {display_path(root, path)} - {entry_title(path)}")
    if affected_knowledge:
        print("knowledge:")
        for path in affected_knowledge:
            print(f"  {display_path(root, path)} - {entry_title(path)}")
    if not affected_info and not affected_knowledge:
        print("No impacted entries found.")
    return 0


def parse_date(value):
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def cmd_stale(args):
    root = kb_root(args)
    count = 0
    for _kind, path in iter_entries(root, "knowledge"):
        data, _body, error = read_entry(path)
        if error:
            continue
        knowledge_updated = parse_date(data.get("updated"))
        if knowledge_updated is None:
            continue
        for dep in list_value(data.get("depends_on")):
            dep_path = resolve_existing_path(root, dep)
            if not dep_path.exists():
                continue
            dep_data, _dep_body, dep_error = read_entry(dep_path)
            if dep_error:
                continue
            dep_updated = parse_date(dep_data.get("updated"))
            if dep_updated and dep_updated > knowledge_updated:
                count += 1
                print(f"{display_path(root, path)} - {data.get('title', '(untitled)')}")
                print(f"  newer dependency: {display_path(root, dep_path)} ({dep_updated.isoformat()})")
    if count == 0:
        print("No stale knowledge found.")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Operate a small local Markdown knowledge base.")
    parser.add_argument("--kb", default=".kb", help="Knowledge base root directory. Default: .kb")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create .kb/source, .kb/info, and .kb/knowledge.")
    init.set_defaults(func=cmd_init)

    new_info = sub.add_parser("new-info", help="Create an info Markdown entry.")
    new_info.add_argument("path")
    new_info.add_argument("--title", required=True)
    new_info.add_argument("--source", action="append", required=True)
    new_info.add_argument("--tag", action="append", default=[])
    new_info.add_argument("--body", help="Markdown body to write at creation time.")
    new_info.add_argument("--body-file", help="Path to a UTF-8 Markdown body file to write at creation time.")
    new_info.add_argument("--body-stdin", action="store_true", help="Read Markdown body from stdin at creation time.")
    new_info.add_argument("--force", action="store_true")
    new_info.set_defaults(func=cmd_new_info)

    new_knowledge = sub.add_parser("new-knowledge", help="Create a knowledge Markdown entry.")
    new_knowledge.add_argument("path")
    new_knowledge.add_argument("--title", required=True)
    new_knowledge.add_argument("--depends-on", action="append", default=[], help="Repeatable. Add one dependency path each time.")
    new_knowledge.add_argument("--tag", action="append", default=[])
    new_knowledge.add_argument("--status", default="draft")
    new_knowledge.add_argument("--body", help="Markdown body to write at creation time.")
    new_knowledge.add_argument("--body-file", help="Path to a UTF-8 Markdown body file to write at creation time.")
    new_knowledge.add_argument("--body-stdin", action="store_true", help="Read Markdown body from stdin at creation time.")
    new_knowledge.add_argument("--force", action="store_true")
    new_knowledge.set_defaults(func=cmd_new_knowledge)

    list_cmd = sub.add_parser("list", help="List info or knowledge entries.")
    list_cmd.add_argument("kind", nargs="?", choices=("info", "knowledge"))
    list_cmd.add_argument("--tag", action="append", default=[])
    list_cmd.add_argument("--status")
    list_cmd.add_argument("--quiet", action="store_true")
    list_cmd.set_defaults(func=cmd_list)

    tree = sub.add_parser("tree", help="Print a folder tree, optionally including Markdown files and titles.")
    tree.add_argument("path", nargs="?", default=".")
    tree.add_argument("--files", action="store_true", help="Show Markdown files.")
    tree.add_argument("--titles", action="store_true", help="Show Markdown titles; implies --files.")
    tree.add_argument("--depth", type=int, help="Maximum directory depth below the requested path.")
    tree.set_defaults(func=cmd_tree)

    read = sub.add_parser("read", help="Read a Markdown entry.")
    read.add_argument("path")
    read.add_argument("--meta-only", action="store_true")
    read.add_argument("--body-only", action="store_true")
    read.add_argument("--head", type=int, help="Print only the first N lines.")
    read.set_defaults(func=cmd_read)

    search = sub.add_parser("search", help="Search titles, tags, and Markdown body without an index.")
    search.add_argument("query", nargs="?")
    search.add_argument("--kind", choices=("info", "knowledge"))
    search.add_argument("--tag", action="append", default=[])
    search.add_argument("--all", dest="all_terms", action="append", default=[], help="Comma-separated or repeated terms; all must match.")
    search.add_argument("--any", dest="any_terms", action="append", default=[], help="Comma-separated or repeated terms; at least one must match.")
    search.add_argument("--context", type=int, default=0, help="Show N lines of context around matching body lines.")
    search.add_argument("--title-only", action="store_true")
    search.set_defaults(func=cmd_search)

    scan = sub.add_parser("scan", help="Validate metadata and references.")
    scan.set_defaults(func=cmd_scan)

    trace = sub.add_parser("trace", help="Trace a knowledge entry to its info dependencies and sources.")
    trace.add_argument("path")
    trace.set_defaults(func=cmd_trace)

    impact = sub.add_parser("impact", help="Find entries impacted by an info or source path.")
    impact.add_argument("path")
    impact.set_defaults(func=cmd_impact)

    stale = sub.add_parser("stale", help="Find knowledge whose info dependencies are newer.")
    stale.set_defaults(func=cmd_stale)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
