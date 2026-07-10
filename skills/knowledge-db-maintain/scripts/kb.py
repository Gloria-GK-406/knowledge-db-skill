#!/usr/bin/env python3
"""Local CLI for kb-core@2 packages with package-owned metadata fields."""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urldefrag, urlsplit


KB_DIRS = ("source", "info", "knowledge")
ALLOWED_STATUS = ("draft", "active", "deprecated", "rejected")
CORE_FIELDS = {
    "schema": {"type": "string", "required": True, "role": "schema", "description": "Core contract version."},
    "kind": {"type": "string", "required": True, "role": "kind", "description": "Entry layer."},
    "title": {"type": "string", "required": True, "role": "title", "description": "Human-readable entry title.", "search": {"enabled": True, "weight": 1000}},
    "status": {"type": "string", "required": True, "role": "status", "description": "Lifecycle status."},
    "updated": {"type": "string", "required": True, "role": "updated", "description": "Last semantic update date."},
    "source": {"type": "string", "multiple": True, "required_for": ["info"], "role": "source", "description": "Evidence references for info."},
    "depends_on": {"type": "string", "multiple": True, "required_for": ["knowledge"], "role": "depends_on", "description": "Info dependencies for knowledge."},
}
CORE_PROFILE = "kb-core@2"
ENTRY_SCHEMA = "kb-entry@2"
PACKAGE_SCHEMA_FILE = "kb-package-schema.json"
SKELETON_ROOT = Path(__file__).resolve().parents[1] / "assets" / "package-skeleton"
MAX_WEIGHT = 1000
SUPPORTED_NORMALIZERS = {"default", "keyword", "upper-case-code", "release-code"}


def kb_root(args): return Path(args.kb).resolve()
def read_utf8_text(path): return path.read_text(encoding="utf-8-sig")
def display_path(root, path):
    try: return path.relative_to(root).as_posix()
    except ValueError: return str(path)


def split_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---": return None, text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---": return "\n".join(lines[1:index]), "\n".join(lines[index + 1:])
    return None, text


def parse_scalar(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'": return value[1:-1]
    if value in {"true", "True", "TRUE"}: return True
    if value in {"false", "False", "FALSE"}: return False
    if value in {"null", "Null", "NULL", "~"}: return None
    if re.fullmatch(r"[+-]?\d+", value): return int(value)
    if re.fullmatch(r"[+-]?(?:\d+\.\d*|\.\d+)(?:[eE][+-]?\d+)?", value): return float(value)
    return value


def parse_simple_yaml(yaml_text):
    """Parse the deliberately small YAML subset used by v2 frontmatter."""
    data, current, nested = {}, None, None
    for raw in yaml_text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"): continue
        if raw.startswith("    - ") and current == "metadata" and nested:
            data["metadata"][nested].append(parse_scalar(raw[6:])); continue
        if raw.startswith("  - ") and current == "metadata" and nested:
            data["metadata"][nested].append(parse_scalar(raw[4:])); continue
        nested_match = re.match(r"^  ([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?$", raw)
        if nested_match and current == "metadata":
            nested, value = nested_match.groups(); value = value or ""
            data["metadata"][nested] = [] if value == "" else parse_scalar(value); continue
        if raw.startswith("  - ") and current and current != "metadata":
            data[current].append(parse_scalar(raw[4:])); continue
        if raw.startswith("- ") and current and current != "metadata":
            data[current].append(parse_scalar(raw[2:])); continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?$", raw)
        if not match: raise ValueError(f"Unsupported YAML line: {raw}")
        key, value = match.groups(); value = value or ""
        if key == "metadata":
            if value: raise ValueError("metadata must be a mapping")
            data[key] = {}; current, nested = key, None
        else:
            data[key] = [] if value == "" else parse_scalar(value); current, nested = key, None
    return data


def read_entry(path):
    text = read_utf8_text(path); yaml_text, body = split_frontmatter(text)
    if yaml_text is None: return {}, body, "missing YAML frontmatter"
    try: return parse_simple_yaml(yaml_text), body, None
    except ValueError as exc: return {}, body, str(exc)


def iter_entries(root, kind=None):
    for entry_kind in ([kind] if kind else ("info", "knowledge")):
        base = root / entry_kind
        if base.exists():
            for path in sorted(base.rglob("*.md")): yield entry_kind, path


def load_schema(root):
    path = root / PACKAGE_SCHEMA_FILE
    if not path.is_file(): raise ValueError(f"missing {PACKAGE_SCHEMA_FILE}")
    try: schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: raise ValueError(f"invalid {PACKAGE_SCHEMA_FILE}: {exc}") from exc
    if not isinstance(schema, dict) or schema.get("schema") != "kb-package-schema@2": raise ValueError("package schema must declare schema 'kb-package-schema@2'")
    if schema.get("extends") != CORE_PROFILE: raise ValueError("package schema must extend 'kb-core@2'")
    fields = schema.get("fields")
    if not isinstance(fields, dict): raise ValueError("package schema fields must be an object")
    for key, field in fields.items(): validate_field_definition(key, field)
    return schema


def validate_field_definition(key, field):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key): raise ValueError(f"invalid field key: {key!r}")
    if key in CORE_FIELDS: raise ValueError(f"package field conflicts with core field: {key}")
    if not isinstance(field, dict): raise ValueError(f"field {key} must be an object")
    if field.get("type") not in {"string", "number", "boolean"}: raise ValueError(f"field {key} type must be string, number, or boolean")
    if not isinstance(field.get("description"), str) or not field["description"].strip(): raise ValueError(f"field {key} requires a description")
    if "multiple" in field and not isinstance(field["multiple"], bool): raise ValueError(f"field {key} multiple must be boolean")
    if "filterable" in field and not isinstance(field["filterable"], bool): raise ValueError(f"field {key} filterable must be boolean")
    if "normalization" in field and field["normalization"] not in SUPPORTED_NORMALIZERS:
        allowed = ", ".join(sorted(SUPPORTED_NORMALIZERS))
        raise ValueError(f"field {key} normalization must be one of {allowed}")
    search = field.get("search", {"enabled": False, "weight": 0})
    if not isinstance(search, dict) or not isinstance(search.get("enabled", False), bool): raise ValueError(f"field {key} search.enabled must be boolean")
    weight = search.get("weight", 0)
    if not isinstance(weight, int) or isinstance(weight, bool) or not 0 <= weight <= MAX_WEIGHT: raise ValueError(f"field {key} search.weight must be an integer from 0 to {MAX_WEIGHT}")
    if not search.get("enabled", False) and weight != 0: raise ValueError(f"field {key} has a weight but is not searchable")
    aliases = field.get("aliases", {})
    if not isinstance(aliases, dict) or any(not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value) for value in aliases.values()): raise ValueError(f"field {key} aliases must map values to string arrays")


def merged_schema(schema):
    fields = {key: {"normalization": "default", **value, "origin": "core"} for key, value in CORE_FIELDS.items()}
    fields.update({key: {"normalization": "default", **value, "origin": "package"} for key, value in schema["fields"].items()})
    return fields


def list_value(value): return value if isinstance(value, list) else ([] if value is None else [value])
def parse_date(value):
    try: return date.fromisoformat(value[:10]) if isinstance(value, str) else None
    except ValueError: return None


def validate_entry(root, kind, path, data, schema):
    problems, rel = [], display_path(root, path)
    def error(message): problems.append(f"{rel}: {message}")
    for key in sorted(set(data) - (set(CORE_FIELDS) | {"metadata"})):
        error(f"unexpected frontmatter field: {key}")
    if data.get("schema") != ENTRY_SCHEMA: error(f"schema should be {ENTRY_SCHEMA!r}")
    if data.get("kind") != kind: error(f"kind should be {kind!r}")
    for key in ("title", "status", "updated"):
        if not isinstance(data.get(key), str) or not data[key].strip(): error(f"missing {key}")
    if data.get("status") not in ALLOWED_STATUS: error(f"status should be one of {', '.join(ALLOWED_STATUS)}")
    if parse_date(data.get("updated")) is None: error("updated should be a valid YYYY-MM-DD date")
    for key in ("source", "depends_on"):
        if key in data and (not isinstance(data[key], list) or not data[key] or not all(isinstance(item, str) and item.strip() for item in data[key])): error(f"{key} must be a non-empty string array")
    role = "source" if kind == "info" else "depends_on"
    if role not in data: error(f"missing {role}")
    metadata = data.get("metadata")
    if metadata is None: metadata = {}
    if not isinstance(metadata, dict): error("metadata must be a mapping"); metadata = {}
    fields = schema["fields"]
    for key in metadata:
        if key not in fields: error(f"undeclared metadata field: {key}")
    for key, definition in fields.items():
        required = definition.get("required", False) or kind in definition.get("required_for", [])
        if required and key not in metadata: error(f"missing required metadata.{key}")
        if key not in metadata: continue
        value = metadata[key]; values = list_value(value)
        if definition.get("multiple", False):
            if not isinstance(value, list): error(f"metadata.{key} must be an array"); continue
        elif isinstance(value, list): error(f"metadata.{key} must be a single value"); continue
        expected = definition["type"]
        for item in values:
            correct = isinstance(item, str) if expected == "string" else (isinstance(item, bool) if expected == "boolean" else isinstance(item, (int, float)) and not isinstance(item, bool))
            if not correct or (expected == "string" and not item.strip()): error(f"metadata.{key} must contain {expected} values")
    if kind == "info":
        for source in list_value(data.get("source")):
            if is_web_source(source): continue
            base = source_reference_base(source)
            if not is_safe_local_reference(base) or not base.startswith("source/"): error(f"local source must point under source/: {source}")
            elif not (root / base).exists(): error(f"source not found: {source}")
    if kind == "knowledge":
        for dep in list_value(data.get("depends_on")):
            if is_web_source(dep) or not dep.startswith("info/") or not dep.endswith(".md") or not is_safe_local_reference(dep): error(f"depends_on must point to info/**/*.md: {dep}")
            elif not (root / dep).exists(): error(f"missing dependency: {dep}")
    return problems


def cmd_schema(args):
    root = kb_root(args)
    try: schema = load_schema(root)
    except ValueError as exc: print(str(exc), file=sys.stderr); return 2
    fields = merged_schema(schema)
    output = {"schema": schema["schema"], "extends": schema["extends"], "fields": fields}
    if args.json: print(json.dumps(output, indent=2, sort_keys=True))
    else:
        for key in sorted(fields):
            field = fields[key]; search = field.get("search", {})
            required = "all" if field.get("required", False) else ",".join(field.get("required_for", [])) or "no"
            aliases = ";".join(f"{value}:{','.join(values)}" for value, values in sorted(field.get("aliases", {}).items())) or "-"
            print(f"{key} ({field['origin']}) type={field['type']} multiple={field.get('multiple', False)} required={required} filterable={field.get('filterable', False)} searchable={search.get('enabled', False)} weight={search.get('weight', 0)} normalization={field.get('normalization', 'default')} aliases={aliases} - {field.get('description', '')}")
    return 0


def normalize_search_text(value):
    text = str(value or ""); text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text); text = text.lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\u4e00-\u9fff/]+", " ", re.sub(r"[_\-\s]+", " ", text))).strip()


def search_tokens(value):
    normal = normalize_search_text(value); tokens = normal.split(); runs = re.findall(r"[\u4e00-\u9fff]+", normal)
    for run in runs:
        for size in (2, 3): tokens.extend(run[index:index + size] for index in range(max(0, len(run) - size + 1)) if len(run) >= size)
    return tokens


def field_match_score(term, text, weight):
    term, text = normalize_search_text(term), normalize_search_text(text)
    if not term or not text: return 0
    if term == text: return weight
    if term in text: return int(weight * 0.80)
    tokens = search_tokens(term)
    return int(weight * 0.55) if tokens and all(token in set(search_tokens(text)) for token in tokens) else 0


def metadata_search_text(key, values, definition):
    aliases = definition.get("aliases", {})
    text = [normalize_filter_value(value, definition) for value in values]
    for value in values:
        normalized_value = normalize_filter_value(value, definition)
        for canonical, alias_values in aliases.items():
            if normalize_filter_value(canonical, definition) == normalized_value:
                text.extend(alias_values)
    return " ".join(map(str, text))


def entry_matches_terms(root, path, data, body, terms, schema):
    metadata = data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {}
    haystack = [data.get("title", ""), body]
    for key, definition in schema["fields"].items():
        if definition.get("search", {}).get("enabled") and key in metadata:
            haystack.append((metadata_search_text(key, list_value(metadata[key]), definition), definition))
    for term in terms:
        if field_match_score(term, data.get("title", ""), 100) or field_match_score(term, body, 100):
            continue
        if not any(field_match_score(normalize_filter_value(term, definition), text, 100) for text, definition in haystack[2:]):
            return False
    return True


def entry_score(root, path, data, body, terms, schema):
    score = 30 if data.get("status") == "active" else 0
    for term in terms:
        score += field_match_score(term, data.get("title", ""), 1000)
        score += field_match_score(term, body, 160)
        metadata = data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {}
        for key, definition in schema["fields"].items():
            search = definition.get("search", {})
            if search.get("enabled") and key in metadata:
                score += field_match_score(normalize_filter_value(term, definition), metadata_search_text(key, list_value(metadata[key]), definition), search.get("weight", 0))
    return score


def parse_filters(raw_filters, schema):
    filters = {}
    for raw in raw_filters or []:
        if "=" not in raw or not raw.split("=", 1)[0] or not raw.split("=", 1)[1]: raise ValueError("--filter must use field=value")
        key, value = raw.split("=", 1)
        definition = schema["fields"].get(key)
        if definition is None: raise ValueError(f"unknown metadata field: {key}")
        if not definition.get("filterable", False): raise ValueError(f"metadata field is not filterable: {key}")
        filters.setdefault(key, []).append(normalize_filter_value(value, definition))
    return filters


def normalize_filter_value(value, definition):
    normalizer = definition.get("normalization", "default")
    if normalizer in {"default", "keyword"}:
        return normalize_search_text(value)
    if normalizer in {"upper-case-code", "release-code"}:
        return re.sub(r"[^A-Za-z0-9]+", "", str(value)).upper()
    return str(value)


def matches_filters(data, filters, schema):
    metadata = data.get("metadata", {})
    return all(
        {normalize_filter_value(value, schema["fields"][key]) for value in list_value(metadata.get(key))} & set(values)
        for key, values in filters.items()
    )


def load_query_schema(args):
    try: return load_schema(kb_root(args))
    except ValueError as exc: raise SystemExit(str(exc)) from exc


def cmd_list(args):
    root = kb_root(args); schema = load_query_schema(args)
    try: filters = parse_filters(args.filter, schema)
    except ValueError as exc: print(str(exc), file=sys.stderr); return 2
    count = 0
    for _kind, path in iter_entries(root, args.kind):
        data, _body, error = read_entry(path)
        if error or validate_entry(root, _kind, path, data, schema):
            continue
        if (not args.status or data.get("status") == args.status) and matches_filters(data, filters, schema):
            count += 1; print(f"{display_path(root, path)} - {data.get('title', '(untitled)')}")
    if not count and not args.quiet: print("No entries found.")
    return 0


def cmd_search(args):
    root = kb_root(args); schema = load_query_schema(args)
    try: filters = parse_filters(args.filter, schema)
    except ValueError as exc: print(str(exc), file=sys.stderr); return 2
    terms = [value for value in [args.query, *args.all_terms, *args.any_terms] if value and value.strip()]
    if not terms and not filters: print("search requires a query or --filter.", file=sys.stderr); return 2
    results = []
    for _kind, path in iter_entries(root, args.kind):
        data, body, error = read_entry(path)
        if error or validate_entry(root, _kind, path, data, schema) or not matches_filters(data, filters, schema): continue
        if terms and not entry_matches_terms(root, path, data, body, terms, schema): continue
        results.append((-entry_score(root, path, data, body, terms, schema), display_path(root, path), data))
    for _score, rel, data in sorted(results): print(f"{rel} - {data.get('title', '(untitled)')}")
    if not results: print("No matches.")
    return 0


def cmd_scan(args):
    root = kb_root(args); problems = []
    for dirname in KB_DIRS:
        if not (root / dirname).is_dir(): problems.append(f"missing directory: {dirname}/")
    try: schema = load_schema(root)
    except ValueError as exc: problems.append(str(exc)); schema = None
    if schema:
        for kind, path in iter_entries(root):
            data, _body, error = read_entry(path)
            problems.extend([f"{display_path(root, path)}: {error}"] if error else validate_entry(root, kind, path, data, schema))
    if problems:
        for problem in problems: print(f"ERROR: {problem}")
        return 1
    print("OK"); return 0


def cmd_read(args):
    root = kb_root(args); path = root / args.path
    if not path.exists(): print(f"Path not found: {args.path}", file=sys.stderr); return 2
    try: schema = load_schema(root)
    except ValueError as exc: print(str(exc), file=sys.stderr); return 2
    data, body, error = read_entry(path)
    if error:
        print(error, file=sys.stderr); return 1
    problems = validate_entry(root, entry_kind_for_path(root, path), path, data, schema)
    if problems:
        print("; ".join(problems), file=sys.stderr); return 1
    text = read_utf8_text(path); yaml_text, body = split_frontmatter(text)
    print((f"---\n{yaml_text or ''}\n---" if args.meta_only else body if args.body_only else text).rstrip()); return 0


def cmd_trace(args):
    root = kb_root(args); path = root / args.path
    if not path.exists(): print(f"Path not found: {args.path}", file=sys.stderr); return 2
    try: schema = load_schema(root)
    except ValueError as exc: print(str(exc), file=sys.stderr); return 2
    data, _body, error = read_entry(path)
    if error: print(error, file=sys.stderr); return 1
    problems = validate_entry(root, entry_kind_for_path(root, path), path, data, schema)
    if problems:
        print("; ".join(problems), file=sys.stderr); return 1
    print(f"{args.path} - {data.get('title', '(untitled)')}")
    if data.get("kind") == "info":
        for source in list_value(data.get("source")): print(f"  -> {source}")
    elif data.get("kind") == "knowledge":
        for dep in list_value(data.get("depends_on")):
            dep_path = root / dep; dep_data, _body, dep_error = read_entry(dep_path) if dep_path.exists() else ({}, "", "missing")
            print(f"  -> {dep} - {dep_data.get('title', '(missing)')}")
            if not dep_error:
                for source in list_value(dep_data.get("source")): print(f"     -> {source}")
    return 0


def is_web_source(value): return urlsplit(value).scheme in ("http", "https")
def entry_kind_for_path(root, path):
    try:
        kind = path.relative_to(root).parts[0]
    except (ValueError, IndexError):
        return ""
    return kind if kind in ("info", "knowledge") else ""
def source_reference_base(value): return urldefrag(value)[0] if is_web_source(value) else value.split("#", 1)[0].replace("\\", "/")
def is_safe_local_reference(value):
    path = Path(value.replace("\\", "/")); return not path.is_absolute() and ".." not in path.parts


def cmd_init(args):
    root = kb_root(args)
    assets = tuple(sorted(path for path in SKELETON_ROOT.rglob("*") if path.is_file()))
    conflicts = []
    for asset in assets:
        target = root / asset.relative_to(SKELETON_ROOT)
        if target.exists() and (not target.is_file() or target.read_bytes() != asset.read_bytes()):
            conflicts.append(target.relative_to(root).as_posix())
    if conflicts:
        for conflict in conflicts:
            print(f"refusing to overwrite modified package asset: {conflict}", file=sys.stderr)
        return 2
    for name in KB_DIRS: (root / name).mkdir(parents=True, exist_ok=True)
    for asset in assets:
        target = root / asset.relative_to(SKELETON_ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists(): target.write_bytes(asset.read_bytes())
    print(f"Initialized {root}"); return 0


def cmd_tree(args):
    root = kb_root(args); target = root / args.path
    if not target.exists(): print(f"Path not found: {args.path}", file=sys.stderr); return 2
    for path in sorted(target.rglob("*.md")):
        print(display_path(root, path))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Operate a kb-core@2 local Markdown knowledge base.")
    parser.add_argument("--kb", default="."); sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init"); init.set_defaults(func=cmd_init)
    schema = sub.add_parser("schema", help="Show the merged metadata contract."); schema.add_argument("--json", action="store_true"); schema.set_defaults(func=cmd_schema)
    list_cmd = sub.add_parser("list"); list_cmd.add_argument("kind", nargs="?", choices=("info", "knowledge")); list_cmd.add_argument("--filter", action="append", default=[]); list_cmd.add_argument("--status"); list_cmd.add_argument("--quiet", action="store_true"); list_cmd.set_defaults(func=cmd_list)
    search = sub.add_parser("search"); search.add_argument("query", nargs="?"); search.add_argument("--kind", choices=("info", "knowledge")); search.add_argument("--filter", action="append", default=[]); search.add_argument("--all", dest="all_terms", action="append", default=[]); search.add_argument("--any", dest="any_terms", action="append", default=[]); search.set_defaults(func=cmd_search)
    scan = sub.add_parser("scan"); scan.set_defaults(func=cmd_scan); validate = sub.add_parser("validate"); validate.set_defaults(func=cmd_scan)
    read = sub.add_parser("read"); read.add_argument("path"); read.add_argument("--meta-only", action="store_true"); read.add_argument("--body-only", action="store_true"); read.set_defaults(func=cmd_read)
    trace = sub.add_parser("trace"); trace.add_argument("path"); trace.set_defaults(func=cmd_trace)
    tree = sub.add_parser("tree"); tree.add_argument("path", nargs="?", default="."); tree.set_defaults(func=cmd_tree)
    return parser


def extract_global_kb(argv):
    remaining, kb, index = [], None, 0
    while index < len(argv):
        if argv[index] == "--kb" and index + 1 < len(argv): kb = argv[index + 1]; index += 2
        elif argv[index].startswith("--kb="): kb = argv[index].split("=", 1)[1]; index += 1
        else: remaining.append(argv[index]); index += 1
    return kb, remaining


def main(argv=None):
    kb, argv = extract_global_kb(list(sys.argv[1:] if argv is None else argv)); args = build_parser().parse_args(argv)
    if kb is not None: args.kb = kb
    return args.func(args)


if __name__ == "__main__": raise SystemExit(main())
