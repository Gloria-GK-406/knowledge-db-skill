# Routing Decision

- TaskContract: `.rks-agent/tasks/kb-catalog-v3-skill/TaskContract.md`
- Contract revision: `1`
- Task nature: `feature`
- SDD trigger: `Durable package artifact contract and generated producer behavior change.`
- Multi-spec boundary: `no`
- Boundary evidence: `One repository owns the skill documentation, skeleton, generated CI, and tests; one coherent acceptance boundary.`

## Skeleton Economics

- Governed hard floor: `no; no credential, authorization, or irreversible external mutation is in scope.`
- Factors: `Failure consequence 0; Recovery -2; Exposure +2; Error likelihood 0; Rework amplification +2; Detectability -2; Verification feedback cost -1; Continuity +1.`
- Skeleton total: `0`
- Marginal-value justification: `A spec, plan, and review prevent producer/template drift across all later package adoptions.`

- Selected workflow: `single-spec-workflow`
- Selected skeleton: `sdd-standard`
- Selected profile: `code-feature`
- Selection mode: `recommended`
- Execution mode: `auto`
- Overrides and reasons: `None`
