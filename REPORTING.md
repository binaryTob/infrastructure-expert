# REPORTING.md — Report Structure & Evidence Redaction

## Report file

`reports/infrastructure-audit-<YYYY-MM-DD-HHMM>.html` — single, offline, self‑contained HTML (no external CDN; all CSS/JS inline / data‑URI).

## Sections (in order)

1. **Executive Summary** —   overall state, top risks, top recommendations.
2. **Infrastructure Overview** — OS, CPU, RAM, disk, network, containers, Kubernetes, services (cards).
3. **Architecture** — logical diagram (SVG / inline mermaid‑style) of the discovered graph.
4. **Discovered Components** — list with version + source of evidence.
5. **Security Findings** — table: ID, Severity, Finding, Asset, Evidence ref, Impact, Recommendation.
6. **Infrastructure Findings**
7. **Performance Findings**
8. **Reliability Findings**
9. **Observability Findings**
10. **Backup Findings**
11. **Configuration Findings**
12. **Migration Assessment** (if migration objective) — current/target arch, compatibility matrix, gaps, risks, required changes, phases, validation, rollback.
13. **Remediation Plan** — ordered by priority; each entry WHAT/WHY/HOW/RISK/PRIORITY/VALIDATION/ROLLBACK.
14. **Evidence** — referenced evidence records (redacted).
15. **Commands Executed** — command + purpose + safety level + result class.
16. **Skills Used** — skill, purpose, status, findings count.
17. **New Skills Generated** — any SKILL.md created during the run.
18. **References** — official docs / advisories consulted.

## Visual language (offline)

- Severity badges (inlined CSS classes): `crit` red, `high` orange, `med` amber, `low` blue, `info` grey.
- Cards for overview; tables for findings; an architecture diagram drawn as inline SVG from the infrastructure graph.
- A sticky left nav listing sections; severity filter (vanilla JS, no deps).
- Print‑friendly (`@media print`), responsive.

## Evidence record (YAML) — stored under `evidence/<run-id>/`

```yaml
id: <run-id>-<NNN>
run_id: <run-id>
timestamp: <ISO8601>
host: <host>
safety_level: L1 | L2
category: <discovery|security|network|k8s|...>
skill: <skill name>
command: <exact command run>
exit_code: 0
stdout: |
  <redacted output>
stderr: |
  <redacted output>
interpretation: <agent's read of the output>
confidence: HIGH | MEDIUM | LOW
```

## Redaction rules (binding)

Before any stdout/stderr is written to evidence or rendered in the report, run it through `scripts/redact.sh` (or an equivalent inline pass). Patterns redacted to `<<REDACTED:TYPE>>`:

- `-----BEGIN … PRIVATE KEY----- … -----END … PRIVATE KEY-----`
- `password = …`, `password: …`, `pass=…`, `pwd=…`
- `Authorization: Bearer …`, `token=…`, `api[_-]?key=…`, `secret=…`
- `connectionstring`, `mongodb://…:…@`, `postgres://…:…@`
- Kubernetes Secret `data:` base64 values
- Email addresses (optional, configurable)
- Long base64/hex blobs > 40 chars matching key material heuristics

Redaction **always** preserves metadata (where, what type, length, risk) so the report still informs. **The value is never written anywhere persistent.**

## Claim labels (every assertion in the report is one of)

- **FACT** — directly backed by a named evidence id.
- **OBSERVATION** — backed by evidence but interpretation‑dependent.
- **HYPOTHESIS** — reasoned from evidence, not yet tested/verified.
- **RISK** — a potential negative outcome (severity + confidence + exposure + impact).
- **RECOMMENDATION** — the proposed action with remediation template.

A claim labeled FACT without an evidence id is a contract violation.