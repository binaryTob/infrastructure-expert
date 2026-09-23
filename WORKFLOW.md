# WORKFLOW.md — The autonomous reasoning loop

Canonical loop the agent follows for a `full` audit. Other modes (`quick`, `discovery`, `container`, `security`) are subsets — see `workflows/infrastructure-audit.md`.

## 0. Connect

```
verify SSH works (config/target.json)
warm scripts/run_id.sh -> reportes/<run-id>/
record: ssh connectivity proof, login user identity
```

**No assumptions about OS yet.** Discover distribution before assuming any package/manager/init.

## 1. Discover

Run `skills/discovery/system-inventory.md` end-to-end. Broad, cheap, read-only. Capture: OS, kernel, init system, users, services, network, listening ports, firewall, installed packages hinting at runtimes/orchestrators/ingress/databases/WAF/observability, relevant config locations.

Output: `reportes/<run-id>/inventory.yaml` — the raw inventory.

## 2. Classify -> Build graph

From inventory, classify each discovered process/path/port into a component. Build `graph.yaml` edges:

```
Internet -> firewall -> host -> runtime -> orchestrator -> ingress -> service -> workload -> data
```

Also data-plane edges: `port -> process -> service -> container -> app`.

## 3. Select skills

`skills/_index.yaml` is the source of truth for selection. A workflow mode defines a candidate set, not a license to run every entry.

1. Add the transitive `depends_on` closure for every candidate.
2. Topologically order skills so all dependencies run first.
3. Evaluate `triggers` only after prerequisite evidence exists. Multiple triggers are OR; dependencies are AND; an empty trigger list means unconditional within the selected mode.
4. Evaluate block-level `[requires:...]` immediately before the block.
5. Run each skill at most once unless it explicitly declares a resampling policy.
6. Record every skip with a concrete reason: trigger absent, dependency unavailable, insufficient privilege, L2 disabled, or not required by the objective.

An unsupported technology is an inventory fact, not a skill-generation trigger. Continue with step 6.

## 4. Run analysis (per selected skill)

Run the skill's `discovery` then `tests` (all L1/L2) through `scripts/ssh_exec.sh`. Write evidence records into `reportes/<run-id>/evidencia/`. Reuse an evidence record from the current run when target, command parameters and privilege match; do not rerun a command merely because another skill references it. Do not reuse evidence across runs by default.

Execution budget:
- Parallelize at most 3 independent lightweight L1 commands.
- CPU, memory and I/O temporal probes may run concurrently as one coordinated sampling window.
- Serialize host-wide `find`, recursive `grep`, root `du`, container logs, cluster-wide dumps, database queries and temporal probes that touch the same subsystem.
- Never parallelize across unmet dependencies or write two commands to the same evidence id.

For each skill, apply its interpretation rules to the stored evidence and produce candidate findings.

## 5. Find anomalies -> hypotheses -> verify

For each candidate finding, apply the false-positive gate:

```
Evidence?  Context?  Configuration?  Exposure?  Impact?
```

If any is missing -> it's a HYPOTHESIS, run a confirmatory non-destructive test. Only confirmed ones become RISK findings. Update `graph.yaml` with what was learned.

Reassessment: a new edge may select additional skills or bounded ad-hoc checks (loop back to step 3). Stop at a fixed point: no new component, evidence key, graph edge or testable hypothesis. Do not repeat a skill or loop only to gather more data without a stated resampling policy.

## 6. Unsupported technology and skill creation gate

Use this order:

1. Reuse evidence already collected by discovery or another skill.
2. Use an existing generic skill for service, process, network, configuration, logs, security, reliability, observability or backup posture.
3. If the current objective still has a concrete evidence gap, run the smallest bounded L1/L2 ad-hoc check through `scripts/ssh_exec.sh` and record it in `skills-used.yaml` under `ad_hoc_checks`.
4. Persist no new skill unless **all** criteria below are true.

Creation gate (all required):
- **Necessary now:** a current objective or verified hypothesis cannot be answered safely with existing evidence, generic skills or a bounded ad-hoc check.
- **Reusable:** the capability is expected to recur across targets/runs or applies to a reusable class of systems, not just one installed product instance.
- **Distinct:** its evidence contract and interpretation do not substantially overlap an existing skill.
- **Stable:** triggers, commands and interpretation are host-agnostic and based on stable interfaces.
- **Efficient:** it consumes existing evidence where possible and has explicit command ownership; it does not duplicate broad scans.
- **Complete:** it includes false-positive handling, L1/L2 safety, evidence outputs and actionable interpretation.
- **Validated:** schema and catalog validation pass, dependencies are satisfiable, and at least one successful L1/L2 execution verifies the skill.

If any criterion fails, do not create a skill. Record the decision as `not-reusable`, `covered-by-existing-skill`, or `insufficient-evidence`. A close call defaults to no new skill.

When the gate passes, create `skills/<area>/<skill>.md`, add it to `_index.yaml`, execute it once, and record the gate rationale under `new_skills_generated`.

Ad-hoc check record:
```yaml
ad_hoc_checks:
  - id: stable-check-id
    reason: concrete evidence gap
    hypothesis: question being tested
    safety_level: L1
    evidence_refs: [evidence-id]
    status: executed
    persistence_decision: not-reusable
```

## 7. Generate findings -> remediations

Each finding gets the risk model (`lib/severity.md`):
- `id, title, severity(CRITICAL|HIGH|MEDIUM|LOW|INFO), confidence(HIGH|MEDIUM|LOW), asset, evidence refs, impact, likelihood, recommendation, remediation(WHAT/WHY/HOW/RISK/PRIORITY/VALIDATION/ROLLBACK)`.

Write `reportes/<run-id>/findings.yaml`.

## 8. Migration analysis (if migration objective)

*Initially do NOT plan the migration.* First fully document current state (steps 1-7). Then:

1. **Current architecture** (from graph).
2. **Dependency analysis** — what relies on the component being migrated.
3. **Feature inventory** — which features are ACTUALLY used (from evidence on real resources).
4. **Configuration mapping** — map each used feature to the target's equivalent.
5. **Compatibility matrix** per feature: COMPATIBLE / PARTIAL / GAP / NO-EQUIVALENT.
6. **Gaps + risks** -> mitigation per gap.
7. **Migration phases** (ordered, each independently validatable + rollback-able).
8. **Validation plan** per phase.
9. **Rollback plan** per phase.
10. **Readiness score**: Technical / Security / Operational / Compatibility / Observability / Rollback — each 0-100, weighted -> composite.

Write `reportes/<run-id>/migration.yaml`. Only **propose**; never apply (Level 3).

## 9. Generate report

`scripts/gen_report.py reportes/<run-id>/` -> `reportes/<run-id>/informe-<run-id>.html`.
Self-contained offline HTML per `REPORTING.md`. Secret-free (redaction already applied at evidence time + re-checked at render time).

## 10. Print executive summary

To console: host, duration, components discovered, skills executed/skipped, ad-hoc checks, new skills created (normally zero), findings by severity, report path.

## Stop / approval conditions

- Stop the whole run if target identity cannot be verified, redaction fails, or evidence cannot be stored safely.
- If a branch needs Level 3 -> stop that branch, document the exact action and request approval; continue independent read-only branches.
- If a confirmatory test would be destructive -> mark as unverified HYPOTHESIS and recommend manual verification.
- Missing tools, permission denial, timeout or nonzero remote exit -> record `INSUFFICIENT_DATA`, try at most one bounded read-only fallback, then continue.
