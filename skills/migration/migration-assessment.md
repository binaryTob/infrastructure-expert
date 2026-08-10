---
id: "migration_assessment"
name: "Migration Assessment"
version: "1.0"
category: "migration"
phase: "assess"
risk: "advisory"
execution_mode: "auto"
depends_on: ["system_inventory"]
triggers: []
provides: ["migration_readiness", "compatibility_matrix", "migration_phases", "migration_plan"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/migration" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Migration Assessment

Generic A->B migration assessment engine: current state, dependencies, feature inventory,
compatibility matrix, gaps, risks, phases, validation, rollback.

## Rule
NEVER start with the migration plan. Start by fully documenting CURRENT STATE
(source + target analysis). The compatibility matrix MUST be evidence-based
(real config on real resources), not a copy-paste of docs.

## Process

1. Current architecture (from discovery graph).
2. Dependency analysis: what relies on the component being migrated.
3. Feature inventory: which features are ACTUALLY used (from evidence on real resources).
4. Configuration mapping: map each used feature to the target's equivalent.
5. Compatibility matrix per feature: COMPATIBLE / PARTIAL / GAP / NO-EQUIVALENT.
6. Gaps + risks -> mitigation per gap.
7. Migration phases (ordered, each independently validatable + rollback-able).
8. Validation plan per phase.
9. Rollback plan per phase.
10. Readiness score: Technical / Security / Operational / Compatibility / Observability / Rollback.

## Readiness scoring
- Technical (30%): compat % (mapped features / total used features).
- Security (25%): feature parity (no security feature removed without replacement).
- Operational (15%): dual deployment tested, routing verified.
- Compatibility (15%): % fully mapped features.
- Observability (5%): target has monitoring/logging enabled.
- Rollback (10%): can revert to source at any phase.

## Output
- `migration.yaml` with all phases, compatibility matrix, readiness score.
- NEVER apply (Level 3). Only propose.

## Security
Advisory only. No changes applied.
