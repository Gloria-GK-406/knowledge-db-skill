# Package scripts

These scripts operate on this knowledge package. They are intentionally package-local
and contain no migration or query semantics.

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

Build and query behavior are owned by `knowledge-service`. `catalog/build_catalog_from_service.mjs`
only invokes that service's builder to create `catalog.sqlite`; `catalog/sqlite_smoke.py` checks the
resulting artifact. The GitHub Actions workflow orchestrates these scripts and publication.

Before enabling the workflow, set the repository variable
`KNOWLEDGE_SERVICE_REPOSITORY` to the repository that supplies the catalog builder.
Optionally set `KNOWLEDGE_SERVICE_REF`; it defaults to `main`. The workflow deliberately
has no default service repository, so a package cannot publish an artifact with an
implicit environment dependency.
