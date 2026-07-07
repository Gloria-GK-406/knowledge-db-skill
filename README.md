# Knowledge DB Skills

Local Markdown knowledge-base skills for Codex. They organize a knowledge base directly in a repository root:

- `source/`: raw external material stored as files; web pages can also be referenced directly by URL from info entries
- `info/`: organized information extracted from source material
- `knowledge/`: conclusions, procedures, and reusable understanding derived from info

The skills keep provenance explicit: knowledge traces through info to source.

- `knowledge-db-use`: read, search, trace, and answer from an existing local knowledge base.
- `knowledge-db-maintain`: initialize, add, update, delete, and validate a local knowledge base.

## Project Structure

```text
.codex-plugin/plugin.json
skills/knowledge-db-use/SKILL.md
skills/knowledge-db-maintain/SKILL.md
skills/knowledge-db-maintain/scripts/kb.py
skills/knowledge-db-maintain/scripts/kb.ps1
skills/knowledge-db-maintain/scripts/kb.sh
tests/test_kb_cli.py
```

## Usage

Run the CLI from a workspace that contains, or should contain, `source/`, `info/`, and `knowledge/`.

```bash
python skills/knowledge-db-maintain/scripts/kb.py init
python skills/knowledge-db-maintain/scripts/kb.py tree --files --titles
python skills/knowledge-db-maintain/scripts/kb.py scan
```

Use `--kb PATH` to operate on another knowledge-base root.

```bash
python skills/knowledge-db-maintain/scripts/kb.py --kb /path/to/kb scan
```

PowerShell:

```powershell
.\skills\knowledge-db-maintain\scripts\kb.ps1 scan
```

sh/bash:

```bash
sh skills/knowledge-db-maintain/scripts/kb.sh scan
```

Set `KB_PYTHON` when the wrapper should use a specific Python interpreter.

## Testing

```bash
python -m unittest tests.test_kb_cli
```

## License

MIT. See [LICENSE](LICENSE).
