# Workflow: Infrastructure Audit

The main infrastructure analysis workflow. Read-only and reusable across Linux servers accessible over SSH.
The AI session reads `skills/_index.yaml` and this document to coordinate execution.

## Minimum input

| Variable | Required | Default | Description |
|----------|-----------|---------|-------------|
| `SSH_TARGET` | yes | — | `user@host` or a configured SSH alias (`~/.ssh/config`) |
| `MODE` | no | `full` | `full` / `quick` / `discovery` / `container` / `security` |

## Execution diagram

```
CONNECT (verify SSH without assuming the OS)
  |
  v
DISCOVER (skills/discovery — broad, low-cost, read-only)
  |
  v
CLASSIFY -> BUILD INVENTORY -> BUILD GRAPH
  |
  v
DETECT COMPONENTS -> SELECT SKILLS (applicable skills only)
  |
  v
RUN ANALYSIS (selected skills, non-destructive tests)
  |
  v
FIND ANOMALIES -> CREATE HYPOTHESES -> TEST -> VERIFY
  |
  v
GENERATE FINDINGS + REMEDIATIONS
  |
  v
[if migration] MIGRATION ANALYSIS
  |
  v
GENERATE REPORT -> PRINT EXECUTIVE SUMMARY
```

## Hard rules

1. **Read-only.** If a command is not clearly `ro|info|probe` -> STOP -> record a recommendation; do not execute it.
2. **Dynamic detection.** Execute conditional skills only when their `trigger` is satisfied. Otherwise -> SKIP.
3. **No assumptions.** Discover the distribution, init system, container runtime, orchestrator, ingress, databases, WAF, firewall and cloud provider; never assume them.
4. **Evidence first.** No claim about the server without a stored evidence record.
5. **Fact vs hypothesis.** Label every claim as `FACT`, `OBSERVATION`, `HYPOTHESIS`, `RISK` or `RECOMMENDATION`.
6. **Secret redaction.** Detect and report secrets as metadata only (location, type, risk). Redact values before output.
7. **No hardcoded servers.** No `if hostname==`. Base decisions on detected components.
8. **False-positive control.** One snapshot is not a trend. Use `SAMPLE_COUNT >= 4` for inferences.
9. **Reuse evidence.** A skill consumes fresh dependency evidence instead of repeating commands for the same view.
10. **On-demand diagnosis.** Technology presence enables posture/inventory checks, not troubleshooting, deep logs or forensics without a symptom or anomaly.
11. **Exceptional skill creation.** Unsupported technology -> generic skill or bounded ad-hoc check. Persist a skill only after the complete gate in `WORKFLOW.md` passes.
12. **Bounded concurrency.** At most three lightweight independent L1 commands; serialize global scans, logs, database checks, cluster dumps and tests of the same subsystem.

## Modes

| Mode | Selection | Description |
|------|-----------|-------------|
| `full` | `_index.yaml` candidates + triggers | Comprehensive evidence-driven analysis |
| `quick` | minimal set + dependencies | Rapid triage |
| `discovery` | inventory, systemd, processes, network | Discovery and inventory only |
| `container` | Docker/K8s candidates + dependencies | Container host; diagnosis only for anomalies |
| `security` | security posture + dependencies | Security audit |
| `forensic` | forensic candidates + dependencies | Explicit forensic objective/indicators required |

Counts are derived from the catalog and may change. Each mode's sequence is a candidate set; the agent adds dependencies, sorts topologically and evaluates triggers before execution.

## Report directory

Store evidence and reports in `reportes/<run-id>/`:
- `reportes/<run-id>/evidencia/` — per-command YAML records
- `reportes/<run-id>/findings/` — findings
- `reportes/<run-id>/inventory.yaml` — inventory
- `reportes/<run-id>/graph.yaml` — infrastructure graph
- `reportes/<run-id>/informe-<run-id>.html` — offline HTML report

## Technology without a dedicated skill

Do not create a skill merely because a product is present. Record the technology in inventory, reuse generic skills and, if a concrete question remains, run a bounded L1/L2 ad-hoc check through `scripts/ssh_exec.sh`.

Persist a skill only when it is necessary for the current objective, reusable across hosts/runs, non-overlapping, based on stable interfaces, command-efficient and validated through review and execution. See the binding gate in `WORKFLOW.md`.

## Safety levels (see SAFETY.md)

| Level | Name | Scope | Default |
|-------|------|-------|---------|
| 1 | OBSERVE | Read-only commands | Always on |
| 2 | TEST | Non-destructive tests | On by default |
| 3 | CHANGE | Mutating actions | Off — requires explicit approval |
