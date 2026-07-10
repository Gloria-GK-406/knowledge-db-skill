# Knowledge DB Skills

Local Codex skills and a Python CLI for a `kb-core@2` Markdown knowledge base.

Each package has `source/`, `info/`, `knowledge/`, and a root `kb-package-schema.json`. The schema owns all business metadata fields and defines their cardinality, description, exact-filter support, keyword-search support, field weight, and aliases. Entries retain a small fixed core and place package values only under `metadata`.

```text
python skills/knowledge-db-maintain/scripts/kb.py --kb PATH schema
python skills/knowledge-db-maintain/scripts/kb.py --kb PATH scan
python skills/knowledge-db-maintain/scripts/kb.py --kb PATH search "Japan" --filter country=JP
```

Run tests with:

```text
python -m unittest tests.test_kb_cli -v
```
