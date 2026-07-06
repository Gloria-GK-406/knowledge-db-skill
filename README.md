# Knowledge DB Skill

Local Markdown knowledge-base skill for Codex. It organizes a small knowledge base into three layers:

- `source/`: raw external material stored as files; web pages can also be referenced directly by URL from info entries
- `info/`: organized information extracted from source material
- `knowledge/`: conclusions, procedures, and reusable understanding derived from info

The skill keeps provenance explicit: knowledge should trace back through info to source.

## Project Structure

```text
.codex-plugin/plugin.json
skills/knowledge-db/SKILL.md
skills/knowledge-db/scripts/kb.py
skills/knowledge-db/scripts/kb.ps1
skills/knowledge-db/scripts/kb.sh
tests/test_kb_cli.py
```

## Usage

Run the CLI from a workspace that contains, or should contain, `.kb/`.

```bash
python skills/knowledge-db/scripts/kb.py init
python skills/knowledge-db/scripts/kb.py tree --files --titles
python skills/knowledge-db/scripts/kb.py scan
```

`scan` checks local source file existence, web source reachability, and knowledge dependencies.

PowerShell:

```powershell
.\skills\knowledge-db\scripts\kb.ps1 scan
```

sh/bash:

```bash
sh skills/knowledge-db/scripts/kb.sh scan
```

Set `KB_PYTHON` when the wrapper should use a specific Python interpreter.

## Testing

```bash
python -m unittest tests.test_kb_cli
```

## License

MIT. See [LICENSE](LICENSE).
