# Implementation Plan: kb-catalog@3 skill contract

1. Add `kb-package.json` to the package skeleton and include it in the initializer's managed-asset list and rerun-safety tests.
   - Verify an initialized package contains the descriptor and its values are valid.

2. Upgrade the skeleton package checker and catalog builder.
   - Load and validate the descriptor before catalog creation.
   - Change artifact identity to v3; add required package name/description columns and the facet table/index.
   - Populate facets only from filterable metadata and verify aggregation parity in builder tests.

3. Upgrade skeleton smoke and artifact-metadata scripts plus CI template.
   - Require v3 identifiers, v3 schema/columns/tables/indexes, and descriptor-derived metadata.
   - Preserve package-local CI and MinIO publication topology.

4. Update maintain-skill documentation and repository tests/fixtures.
   - Replace v2 producer statements with the breaking v3 contract while retaining kb-core@2 entry semantics.
   - Cover missing/invalid descriptors, v3 generated artifacts, facets, and CLI initialization.

5. Run focused skeleton and CLI tests, then the relevant repository validation suite; review the full diff before acceptance.
