# WORKFLOW.md — The autonomous reasoning loop, narrated

This is the canonical loop the agent follows for a `FULL` audit. Other modes (`DISCOVERY`, `SECURITY`, `MIGRATION`, `PERFORMANCE`, `INCIDENT`) are prefixes/subsets — see `workflows/<mode>.md`.

## 0. Connect

```
verify SSH works (config/target.json)
warm scripts/run_id.sh → evidence/<run-id>/
record: ssh connectivity proof, login user identity
```

**No assumptions about OS yet.** Discover distribution before assuming any package/manager/init.

## 1. Discover (DISCOVERY mode = stop here)

Run `skills/discovery/SKILL.md` end‑to‑end. Broad, cheap, read‑only. Capture: OS, kernel, init system, users, services, network, listening ports, firewall, installed packages hinting at runtimes/orchestrators/ingress/databases/WAF/observability, relevant config locations.

Output: `evidence/<run-id>/inventory.yaml` — the raw inventory.

## 2. Classify → Build graph

From inventory, classify each discovered process/path/port into a component. Build `graph.yaml` edges:

```
Internet → firewall → host → runtime → orchestrator → ingress → service → workload → data
```

Also data‑plane edges: `port → process → service → container → app`.

## 3. Select skills

For every `<area>/<tech>/SKILL.md`, check `applies_when`. Select the matching set.

If a present technology has **no** skill → generate one (see step 5).

## 4. Run analysis (per selected skill)

Run the skill's `discovery` then `tests` (all L1/L2). Write evidence records. For each, run `interpretation` rules → candidate findings.

## 5. Find anomalies → hypotheses → verify

For each candidate finding, apply the false‑positive gate:

```
Evidence?  Context?  Configuration?  Exposure?  Impact?
```

If any is missing → it's a HYPOTHESIS, run a confirmatory non‑destructive test. Only confirmed ones become RISK findings. Update `graph.yaml` with what was learned (e.g. `hostNetwork: true` pulls a network exposure edge).

Reassessment: a new edge may select **additional** skills (loop back to step 3).

## 6. Dynamic skill generation

Trigger: present technology, no `SKILL.md`. Steps:

1. Identify the technology (binary, version, config path, units).
2. Draft `skills/<area>/<tech>/SKILL.md` per `SKILLS.md` schema (applies_when + discovery + tests + interpretation + remediation_template).
3. Validate the schema.
4. Run it (L1/L2 only), capture evidence.
5. Persist the `SKILL.md` for reuse.
6. Record under "New Skills Generated" in the report.

## 7. Generate findings → remediations

Each finding gets the risk model (`lib/severity.md`):
`id, title, severity(CRITICAL|HIGH|MEDIUM|LOW|INFO), confidence(HIGH|MEDIUM|LOW), asset, evidence refs, impact, likelihood, recommendation, remediation(WHAT/WHY/HOW/RISK/PRIORITY/VALIDATION/ROLLBACK)`.

Write `evidence/<run-id>/findings.yaml`.

## 8. Migration analysis (if migration objective)

*Initially do NOT plan the migration.* First fully document current state (steps 1–7). Then:

1. **Current architecture** (from graph).
2. **Dependency analysis** — what relies on the component being migrated.
3. **Feature inventory** — which features are ACTUALLY used (from evidence on real resources, not docs).
4. **Configuration mapping** — map each used feature to the target's equivalent (use compatibility tables from `lib/compat/`; create if absent).
5. **Compatibility matrix** per feature: COMPATIBLE / PARTIAL / GAP / NO-EQUIVALENT.
6. **Gaps + risks** → mitigation per gap.
7. **Migration phases** (ordered, each independently validatable + rollback‑able).
8. **Validation plan** per phase.
9. **Rollback plan** per phase.
10. **Readiness score** (see `REPORTING.md`): Technical / Security / Operational / Compatibility / Observability / Rollback — each 0–100, weighted → composite.

Write `evidence/<run-id>/migration.yaml`. Only **propose**; never apply (Level 3). The migration analysis is generic: any source-to-target technology migration uses the same evidence-based mapping process.

## 9. Generate report

`scripts/gen_report.py evidence/<run-id> > reports/infrastructure-audit-<ts>.html`. Self‑contained offline HTML per `REPORTING.md`. Secret‑free (redaction already applied at evidence time + re‑checked at render time).

## 10. Print executive summary

To console: host, duration, components discovered, skills executed, new skills created, findings by severity, report path.

## Stop / approval conditions

- A Level 3 action is needed → STOP, DOCUMENT, REQUEST APPROVAL, do not proceed.
- A confirmatory test would be destructive (e.g. need to restart to reproduce) → mark as unverified HYPOTHESIS, recommend the operator verify manually.