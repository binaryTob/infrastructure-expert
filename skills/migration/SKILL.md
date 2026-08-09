---
name: migration-assessment
area: migration
description: Generic technology-A→B migration assessment engine: current state, deps, feature inventory, compatibility matrix, gaps, risks, phases, validation, rollback.
purpose: For any migration objective, map what-is-actually-used→target-equivalent and score readiness from evidence.
safety: L1
prerequisites:
  - "source technology inventory complete (discovery + source skill)"
  - "target technology inventory complete (target skill)"
applies_when:
  - "migration objective present in config/target.json"
inputs:
  - "In-use feature set from source skill (e.g. ingress annotations, config directives)"
  - "Target provider config from target skill (e.g. Helm values, daemon args)"
discovery: []  # uses evidence from source+target skills
tests: []
evidence_artifacts: []  # populated dynamically at runtime
interpretation: |
  For each distinct SOURCE feature (from real config, NOT docs):
    1. Map to TARGET equivalent (see lib/compat/<source>-to-<target>.md).
    2. Classify: COMPATIBLE (target supports directly), PARTIAL (substitution works in specific cases), GAP (no equivalent, lost functionality), NO-EQUIVALENT (fundamentally different).
    3. For GAPs, state impact (which vhost, which path, what breaks).
    4. Build the phases list:
       Phase 0: Pre-migration (understand current state — done by this loop).
       Phase 1: Deploy target with compat provider (duplicate routing, validate in parallel).
       Phase 2: Verify ALL reachable host/path combos (curl every vhost/path).
       Phase 3: Migrate simple hosts first (no regex/capture-groups → confirm parity).
       Phase 4: Migrate complex hosts (regex, custom config) -> write target-native resources.
       Phase 5: Remove source controller (if not already).
       Phase 6: Remove redundant objects (drift cleanup).
       Each phase: WHAT, VALIDATION (read-only curl per host), ROLLBACK (revert to previous step).
    5. Compute readiness: Technical (compat %), Security (feature parity), Operational (both controllers deployed? dual-routing tested?), Compatibility (% fully mapped), Observability (target logs enabled?), Rollback (can revert to source?).
        Composite = weighted average (Technical 30, Security 25, Operational 15, Compat 15, Obs 5, Rollback 10).
risk_model: |
  Security feature removal without replacement = CRITICAL.
  Broken host (503 on production vhosts) = HIGH.
  Unverified compatibility for complex features = HIGH.
  Dual routing drift risk = MEDIUM.
remediation_template: ~
references: []
---

# Migration Assessment

THE RULE: never start with the migration plan. Start by fully documenting CURRENT
STATE (source + target analysis). The compatibility matrix
MUST be evidence-based (real config on real resources), not a copy-paste
of docs. For every CELL in the matrix, cite the resource AND the test result.
