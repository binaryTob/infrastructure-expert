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

For every skill in `skills/_index.yaml`, check `applies_when`/`triggers`. Select the matching set. Conditional skills (docker, kubernetes, database, traefik) run only if their trigger is detected.

If a present technology has **no** skill -> generate one (see step 6).

## 4. Run analysis (per selected skill)

Run the skill's `discovery` then `tests` (all L1/L2). Write evidence records into `reportes/<run-id>/<skill>/`. For each, run `interpretation` rules -> candidate findings.

## 5. Find anomalies -> hypotheses -> verify

For each candidate finding, apply the false-positive gate:

```
Evidence?  Context?  Configuration?  Exposure?  Impact?
```

If any is missing -> it's a HYPOTHESIS, run a confirmatory non-destructive test. Only confirmed ones become RISK findings. Update `graph.yaml` with what was learned.

Reassessment: a new edge may select **additional** skills (loop back to step 3).

## 6. Dynamic skill generation

Trigger: present technology, no `SKILL.md`. Steps:

1. Identify the technology (binary, version, config path, units).
2. Draft `skills/<area>/<tech>/SKILL.md` per `_template.md` schema.
3. Validate against `_schema.yaml`.
4. Run it (L1/L2 only), capture evidence.
5. Persist the `SKILL.md` for reuse.
6. Record under "New Skills Generated" in the report.

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

To console: host, duration, components discovered, skills executed, new skills created, findings by severity, report path.

## Stop / approval conditions

- A Level 3 action is needed -> STOP, DOCUMENT, REQUEST APPROVAL, do not proceed.
- A confirmatory test would be destructive -> mark as unverified HYPOTHESIS, recommend manual verification.
