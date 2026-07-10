# Package scripts

These scripts operate on this knowledge package. They are intentionally package-local
and compile the package without importing or checking out a query service.

`check_package.py` requires [PyYAML](https://pyyaml.org/). Install it with
`python -m pip install PyYAML` when it is not already available.

Run the read-only metadata, layout, and local-reference check:

```powershell
python scripts/check_package.py --kb .
```

Run the catalog helper tests:

```powershell
python -m unittest scripts.catalog.test_metadata -v
```

Build a self-contained v2 SQLite catalog:

```powershell
python -m scripts.catalog.build_catalog --kb . --package-name <package-name> --revision <git-sha> --out <output-directory>
```

The builder validates `kb-package-schema.json` and every entry before writing
`catalog.sqlite`. On validation failure it writes `validation-report.json` and does
not produce a catalog. `catalog/sqlite_smoke.py` checks the resulting artifact. The
GitHub Actions workflow orchestrates these scripts and publication.
