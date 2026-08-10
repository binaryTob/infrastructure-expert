# Infrastructure Expert

**Autonomous infrastructure analysis agent** powered by AI. Connects to a remote Linux server over SSH, discovers its real architecture from evidence (never from assumptions), runs non-destructive tests, and produces a professional offline HTML report covering security, networking, Kubernetes, performance, reliability, observability, backups, and migration readiness.

The "agent" is an AI coding session reading `AGENTS.md` + `workflows/` + `skills/`. There is no daemon; everything is reproducible from evidence stored in `reportes/`.

## What it does

- **Discovery** — OS, kernel, init system, CPU, RAM, disks, users, services, network, firewall, containers, Kubernetes, ingress, databases, observability stack.
- **Resource analysis** — CPU load, memory pressure, disk usage, I/O bottlenecks, process ranking, network exposure.
- **Security audit** — SSH posture, privilege surface, Pod Security, NetworkPolicies, TLS, WAF, secrets metadata (values redacted).
- **Platform analysis** — Docker containers, Kubernetes (nodes, pods, workloads, services, ingress, RBAC, storage), ingress-nginx features, Traefik providers/middlewares.
- **Performance & reliability** — resource trends, SPOF detection, HA assessment, etcd health.
- **Observability** — monitoring stack health, metrics availability, logging pipeline.
- **Backup assessment** — detect backup mechanisms, verify etcd snapshots, PVC backup coverage.
- **Migration assessment** — generic A->B migration engine: feature mapping, compatibility matrix, gaps, phases, rollback plan.

## Quick start

```bash
# 1. Clone
git clone <repo-url>
cd infrastructure-expert

# 2. Configure the target (never commit this file)
cp config/target.example.json config/target.json
# Edit: host, port, user, private_key

# 3. Run an audit — ask the AI agent:
#   "Run the infrastructure audit workflow on the configured target."
#   Modes: full | quick | discovery | container | security
```

### Output

All scan data and reports are stored in `reportes/<run-id>/`:
- `reportes/<run-id>/evidencia/` — evidence records (YAML, redacted)
- `reportes/<run-id>/findings.yaml` — structured findings
- `reportes/<run-id>/inventory.yaml` — discovered inventory
- `reportes/<run-id>/graph.yaml` — infrastructure graph
- `reportes/<run-id>/informe-<run-id>.html` — self-contained offline HTML report
- Executive summary printed to the console.

## Safety

| Level | Description | Default |
|-------|-------------|---------|
| **L1 — OBSERVE** | Read-only commands (`kubectl get`, `cat`, `ss`, `ls`) | Always on |
| **L2 — TEST** | Non-destructive tests (`curl`, `openssl s_client`) | Always on |
| **L3 — CHANGE** | Mutating commands (`kubectl apply`, service restart, config edit) | **Off** — requires explicit per-action approval |

The agent **never** automatically: restarts services, edits configs, installs packages, deletes files, or runs `kubectl apply/delete`.

## How it works

```
CONNECT (verify SSH, no OS assumptions yet)
  |
  v
DISCOVER (skills/discovery — broad, cheap, read-only)
  |
  v
CLASSIFY -> BUILD INVENTORY -> BUILD GRAPH
  |
  v
SELECT SKILLS (only those matching what was discovered)
  |
  v
RUN ANALYSIS (non-destructive tests per skill)
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
GENERATE HTML REPORT -> PRINT EXECUTIVE SUMMARY
```

If a technology is detected that has no corresponding skill, the agent **dynamically generates one**, runs it, and persists it for future audits.

## Repository structure

```
infrastructure-expert/
├── AGENTS.md              <- operating contract for the AI agent
├── README.md              <- project overview
├── ARCHITECTURE.md        <- how the framework fits together
├── WORKFLOW.md            <- the autonomous reasoning loop
├── SKILLS.md              <- skill schema + how to create skills
├── REPORTING.md           <- report structure + redaction rules
├── SAFETY.md              <- safety levels + forbidden actions
├── .gitignore             <- excludes config/target.json, reportes/
├── config/
│   └── target.example.json
├── scripts/               <- ssh_exec.sh, redact, run_id, gen_report
├── lib/
│   └── severity.md        <- severity matrix
├── skills/                <- 22 skills in 10 categories
│   ├── _index.yaml        <- master catalog
│   ├── _schema.yaml       <- skill contract
│   ├── _template.md       <- canonical template
│   ├── common/helpers.md  <- reusable modules
│   ├── discovery/         <- system-inventory, systemd-analysis (services + resources)
│   ├── resources/         <- cpu, memory, disk, io, process, network
│   ├── platform/          <- docker, kubernetes, ingress-nginx, traefik, database
│   ├── security/          <- security-analysis
│   ├── analysis/          <- configuration, log, capacity, optimization
│   ├── reliability/       <- reliability-analysis
│   ├── observability/     <- observability-analysis
│   ├── backup/            <- backup-analysis
│   └── migration/         <- migration-assessment
├── workflows/
│   ├── infrastructure-audit.md
│   └── server-resource-analysis.md
├── templates/             <- report templates
└── reportes/              <- scan data + reports (gitignored)
```

## Available skills (22)

| Skill | Category | Phase | Trigger |
|-------|----------|-------|---------|
| system-inventory | discovery | discover | always |
| systemd-analysis | systemd | discover | always |
| cpu-analysis | cpu | analyze | always |
| memory-analysis | memory | analyze | always |
| disk-analysis | disk | analyze | always |
| io-analysis | io | analyze | always |
| process-analysis | process | analyze | always |
| network-analysis | network | analyze | always |
| docker-analysis | docker | analyze | PRESENT:docker |
| kubernetes-analysis | kubernetes | analyze | PRESENT:kubectl |
| ingress-nginx-analysis | ingress | analyze | PRESENT:ingress-nginx |
| traefik-analysis | ingress | analyze | PRESENT:traefik |
| database-analysis | database | analyze | PRESENT:postgresql/mysql/redis |
| security-analysis | security | analyze | always |
| configuration-analysis | configuration | analyze | always |
| log-analysis | logging | analyze | depends on disk |
| reliability-analysis | reliability | analyze | PRESENT:kubectl |
| observability-analysis | observability | analyze | always |
| backup-analysis | backup | analyze | always |
| capacity-analysis | capacity | correlate | depends on 5 previous |
| optimization-analysis | optimization | optimize | depends on capacity |
| migration-assessment | migration | assess | always |

## Workflows

| Workflow | Skills | Description |
|----------|--------|-------------|
| `full` | 22 | Complete infrastructure analysis |
| `quick` | 9 | Fast health triage |
| `discovery` | 4 | Discovery and inventory only |
| `container` | 8 | Container host focus |
| `security` | 7 | Security audit |

## Creating a skill

See `SKILLS.md` and `skills/_template.md`. Create `skills/<area>/<skill>.md`:

1. Copy `skills/_template.md` -> `skills/<area>/<new-skill>.md`.
2. Fill frontmatter (id, name, category, phase, risk, depends_on, provides, triggers, parameters, output).
3. Write commands (with `[risk:ro|info|probe] [mode:auto]` tags).
4. Write analysis, false positives, thresholds, evidence, security.
5. Add entry in `skills/_index.yaml` under `skills:` and optional workflow.

## Requirements

- `python3` + `pyyaml` — for report generation and redaction
- `ssh` — connectivity to the target host
- An AI coding agent (opencode / Claude Code style) that reads `AGENTS.md`

No other dependencies. Skills are plain text instructions, not executable code.

## Security

- **Secrets are never stored.** `scripts/redact.py` strips passwords, tokens, keys, and connection strings before evidence is written to disk.
- **No credentials are committed.** `config/target.json`, `reportes/` are gitignored.
- **Read-only by default.** Mutations require explicit operator approval per `SAFETY.md`.
- **Completely reusable.** Only `config/target.json` changes between scans. No hardcoded hostnames.
- **No scan history in repo.** All evidence, reports, and scan data go into `reportes/` which is gitignored.

## License

MIT
