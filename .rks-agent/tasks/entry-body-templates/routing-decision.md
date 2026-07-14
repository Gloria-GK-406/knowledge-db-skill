# Routing Decision

- TaskContract: `.rks-agent/tasks/entry-body-templates/TaskContract.md`
- Contract revision: `1`
- Task nature: `feature`
- Multi-spec boundary: `no`
- Boundary evidence: `One coherent acceptance boundary covers documentation, scaffolding, validation, and tests for one entry-body contract.`

| Dimension | Score | Evidence |
| --- | ---: | --- |
| Change footprint | 1 | Multiple files within the knowledge-db-maintain skill component. |
| Execution shape | 1 | Contract, implementation, validation, and closeout are ordered stages. |
| Uncertainty | 1 | Existing CLI and generated-checker integration points require bounded investigation. |
| Risk | 1 | Changes the package validation and CLI interface. |
| Verification | 1 | Requires CLI, generated checker, skill, and repository tests. |
| Continuity | 0 | Expected to complete in one session. |
| **Total** | **5** | |

- Selected workflow: `single-spec-workflow`
- Selected skeleton: `sdd-lite`
- Selected profile: `code-feature`
- Selection mode: `recommended`
- Execution mode: `auto`
- Overrides and reasons: `None; the behavior boundary is durable but the implementation path is direct and does not need a separate plan.`
