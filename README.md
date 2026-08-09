# Infrastructure Expert

An **autonomous infrastructure analysis agent** powered by AI. Connects to a remote Linux server over SSH, discovers its real architecture from evidence (never from assumptions), runs non-destructive tests, and produces a professional offline HTML report covering security, networking, Kubernetes, performance, reliability, observability, backups, and migration readiness.

The "agent" is an AI coding session running `AGENTS.md` + `workflows/` + `skills/`. There is no daemon; everything is reproducible from evidence stored on disk.

## What it does

- **Discovery** — OS, kernel, init system, CPU, RAM, disks, users, services, network, firewall, containers, Kubernetes, ingress, databases, observability stack.
- **Security audit** — SSH posture, privilege surface, Pod Security, NetworkPolicies, TLS, WAF, secrets metadata (values redacted).
- **Networking analysis** — interfaces, routes, listening ports, process mapping, firewall rules, CNI, edge ingress path.
- **Kubernetes deep-dive** — nodes, pods, services, ingress, workloads, Helm releases, RBAC, storage classes, PVCs.
- **Ingress controller analysis** — ingress-nginx (annotations, WAF, rewrite rules), Traefik (providers, entrypoints, middlewares, TLS).
- **Performance, reliability, observability** — resource usage, SPOF detection, HA assessment, monitoring stack health.
- **Backup assessment** — detect backup mechanisms, verify etcd snapshots, PVC backup coverage.
- **Migration assessment** — generic engine to evaluate any technology A→B migration: feature mapping, compatibility matrix, gaps, phases, rollback plan.

## Quick start

```bash
# 1. Clone and configure
git clone https://github.com/user/infra-expert.git
cd infra-expert

# 2. Configure the target (never commit this file)
cp config/target.example.json config/target.json
# Edit: host, port, user, private_key, objective

# 3. Run an audit — ask the AI agent:
#   "Run the infrastructure audit workflow on the configured target."
#   Modes: DISCOVERY | SECURITY | MIGRATION | PERFORMANCE | INCIDENT | FULL
```

### Output

- `evidence/<run-id>/*.yaml` — every evidence record, redacted and reproducible.
- `reports/infrastructure-audit-<timestamp>.html` — self-contained offline HTML report.
- Executive summary printed to the console.

## Safety

| Level | Description | Default |
|-------|-------------|---------|
| **L1 — OBSERVE** | Read-only commands (`kubectl get`, `cat`, `ss`, `ls`). | Always on |
| **L2 — TEST** | Non-destructive tests (`curl`, `openssl s_client`). | Always on |
| **L3 — CHANGE** | Mutating commands (`kubectl apply`, service restart, config edit). | **Off** — requires explicit per-action approval |

The agent **never** automatically: restarts services, edits configs, installs packages, deletes files, or runs `kubectl apply/delete`.

## How it works

```
CONNECT (verify SSH, no OS assumptions yet)
  ↓
DISCOVER (skills/discovery — broad, cheap, read-only)
  ↓
CLASSIFY → BUILD INVENTORY → BUILD GRAPH
  ↓
SELECT SKILLS (only those matching what was discovered)
  ↓
RUN ANALYSIS (non-destructive tests per skill)
  ↓
FIND ANOMALIES → CREATE HYPOTHESES → TEST → VERIFY
  ↓
GENERATE FINDINGS + REMEDIATIONS
  ↓
[if migration] MIGRATION ANALYSIS
  ↓
GENERATE HTML REPORT → PRINT EXECUTIVE SUMMARY
```

If a technology is detected that has no corresponding skill, the agent **dynamically generates one**, runs it, and persists it for future audits.

## Repository structure

```
infra-expert/
├── AGENTS.md            ← operating contract for the AI agent
├── ARCHITECTURE.md      ← how the framework fits together
├── WORKFLOW.md          ← the autonomous reasoning loop
├── SKILLS.md            ← skill schema + how to create skills
├── REPORTING.md         ← report structure + redaction rules
├── SAFETY.md            ← safety levels + forbidden actions
├── config/              ← target.json (gitignored), target.example.json
├── scripts/             ← SSH wrapper, redaction, report generator
├── lib/                 ← shared helpers (severity matrix)
├── skills/              ← one folder per capability; SKILL.md each
├── workflows/           ← entry points per mode
├── evidence/<run-id>/   ← YAML evidence records (gitignored)
└── reports/             ← generated HTML reports
```

## Available skills

| Skill | Area | Description |
|-------|------|-------------|
| `system-discovery` | discovery | Broad OS/host discovery — the entry point |
| `security-analysis` | security | Defensive posture: SSH, PSA, RBAC, TLS, secrets |
| `networking-analysis` | networking | Interfaces, routes, ports, firewall, CNI |
| `kubernetes-analysis` | kubernetes | Cluster state: nodes, workloads, services, storage |
| `ingress-nginx-analysis` | ingress-nginx | Ingress controller feature inventory |
| `traefik-analysis` | traefik | Traefik deployment: providers, middlewares, TLS |
| `performance-analysis` | performance | Resource usage, bottlenecks, capacity |
| `reliability-analysis` | reliability | HA assessment, SPOF detection, etcd health |
| `observability-analysis` | observability | Monitoring stack: metrics, logs, alerts |
| `backup-analysis` | backup | Detection of backup mechanisms, restore readiness |
| `migration-assessment` | migration | Generic A→B migration engine |

## Creating a skill

See `SKILLS.md`. Create `skills/<area>/<tech>/SKILL.md`:

```yaml
---
name: my-skill
area: <area>
description: one-liner
purpose: what the agent achieves
safety: L1 | L2
applies_when:
  - "detection command"
discovery:
  - "read-only commands"
tests:
  - "non-destructive tests"
interpretation:
  - "evidence → finding rules"
risk_model: severity assignment guidance
---

# Skill body
```

## Requirements

- `python3` + `pyyaml` — for report generation
- `ssh` — connectivity to the target host
- An AI coding agent (opencode / Claude Code style) that reads `AGENTS.md`

No other dependencies. Skills are plain text instructions, not executable code.

## Security

- **Secrets are never stored.** `scripts/redact.sh` strips passwords, tokens, keys, and connection strings before evidence is written to disk.
- **No credentials are committed.** `config/target.json`, `evidence/`, and `reports/` are gitignored.
- **Read-only by default.** Mutations require explicit operator approval per `SAFETY.md`.

## License

MIT
