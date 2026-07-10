# Task 1 report: generic package skeleton initialization

## Delivered

- Added `skills/knowledge-db-maintain/assets/package-skeleton/` with the generic v2 package schema, package checker, catalog helpers, and catalog-artifact workflow.
- Changed `kb init` to materialize the complete skeleton plus `source/`, `info/`, and `knowledge/` directories.
- `init` is repeatable only when every existing generated asset is byte-identical; it preflights all assets and returns exit code 2 with one strict conflict per modified asset before it writes anything.
- Empty `source/`, `info/`, and `knowledge/` directories are preserved with generated `.gitkeep` assets.
- A directory placed where an asset file belongs is treated as a preflight conflict, with no traceback or partial materialization.
- Replaced package-specific catalog test names and object paths with `example-org/example-knowledge-package`.
- The workflow requires an explicit `KNOWLEDGE_SERVICE_REPOSITORY` repository variable and no longer defaults to an organization-specific service repository.

## TDD evidence

1. Added initialization-success and modified-asset conflict tests in `tests/test_kb_cli.py`.
2. RED: both failed because the prior command made only three directories and a minimal schema.
3. GREEN: `py -3 -m unittest tests.test_kb_cli.KbCliV2Tests.test_init_materializes_the_complete_generic_package_skeleton tests.test_kb_cli.KbCliV2Tests.test_init_refuses_to_overwrite_a_changed_skeleton_asset -v` passed (2/2).
4. Regression: with `PYTHONIOENCODING=utf-8`, `py -3 -m unittest tests.test_kb_cli -v` passed (18/18).
5. Generated-package verification: `python -m unittest scripts.catalog.test_metadata -v` passed (2/2) after `kb init`; the generated `scripts/check_package.py --kb <temp-package>` also passed.

## Package-specific content audit

`rg -i "s4hana|sap-btp|process.navigator|\\b2602\\b" assets/package-skeleton` returned no matches. The template contains no SAP content or values, and only uses CI secret *names* such as `MINIO_ACCESS_KEY`; it does not include credentials.

## Follow-up contract concern

The copied verified workflow and its catalog helper smoke test still require the service's current v1 SQLite tables (`packages`, `entries`, `entry_lines`, `info_sources`, `knowledge_dependencies`, `entries_fts`). This task deliberately did not alter the service contract. When the planned v2 service builder lands, its generic table requirements must be updated in both the package skeleton workflow and `test_metadata.py`; otherwise the template will fail its artifact smoke stage against a v2-only catalog.
