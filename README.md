# Infrastructure Expert

**Evidence-driven Linux infrastructure analysis through an AI coding agent.**
The operator's local agent session uses SSH to collect evidence, selects relevant
analysis skills and produces an offline HTML report. The catalog covers security,
networking, containers, Kubernetes, performance, reliability, observability,
backups and migration readiness; applicability depends on what is discovered.

The "agent" is an AI coding session reading `AGENTS.md` + `workflows/` + `skills/`.
There is no daemon or autonomous Python orchestration engine. The session reasons
about evidence and writes inventory, graph and findings; Python/Bash provide SSH
capture, heuristic redaction, catalog validation and HTML rendering. Evidence
stored in `reportes/` supports review; it is not a tamper-evident forensic chain.

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
git clone https://github.com/binaryTob/infrastructure-expert.git
cd infrastructure-expert
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
source .venv/bin/activate

# 2. Configure the target (never commit this file)
cp config/target.example.json config/target.json
# Edit: host, port, user, private_key
# The supplied 192.0.2.10 address is reserved for documentation, not a live target.

# 3. Run an audit — ask the AI agent:
#   "Run the infrastructure audit workflow on the configured target."
#   Modes: full | quick | discovery | container | security
```

Obtain authorization for the exact host and any application/cluster probes first.
Use an AI coding session rooted in this repository that reads `AGENTS.md`. The
skills are catalog Markdown documents, not OpenCode `SKILL.md` auto-discovery
packages; the workflow loads them explicitly. The target does not need this repo
or an AI runtime installed.

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

This is an **operator/agent contract**, supported by a regex mutability blocklist
in `scripts/ssh_exec.sh`; it is not an execution sandbox or proof that arbitrary
shell text is read-only. Use a least-privilege SSH account and review payloads.
The wrapper accepts L1/L2 only. L3 actions require separate per-action approval;
the wrapper does not provide a mutation executor.

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

If a technology has no dedicated skill, the agent first reuses generic capabilities or runs a bounded read-only ad-hoc check. It persists a new skill only when the capability is necessary, non-overlapping, host-agnostic, validated, and expected to be reused across targets or runs.

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
├── skills/                <- curated capabilities; count derived from _index.yaml
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

## Representative skills

`skills/_index.yaml` is the complete source of truth. This table highlights the core capabilities only; do not use it for selection or counts.

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
| reliability-analysis | reliability | analyze | workflow candidate + dependencies |
| observability-analysis | observability | analyze | always |
| backup-analysis | backup | analyze | always |
| capacity-analysis | capacity | correlate | depends on 5 previous |
| optimization-analysis | optimization | optimize | depends on capacity |
| migration-assessment | migration | assess | OBJECTIVE:migration |

## Workflows

| Workflow | Selection | Description |
|----------|-----------|-------------|
| `full` | catalog candidates + triggers | Complete evidence-driven analysis |
| `quick` | minimal candidates + dependencies | Fast health triage |
| `discovery` | 4 base capabilities | Discovery and inventory only |
| `container` | Docker/K8s candidates + dependencies | Container host focus |
| `security` | security candidates + dependencies | Security audit |

Counts are derived from `skills/_index.yaml`; conditional and diagnostic skills are skipped unless their trigger is satisfied.

## Creating a skill

Do not create a skill merely because a technology was discovered. First use existing evidence, a generic skill, or a bounded ad-hoc check. Only after the creation gate in `WORKFLOW.md` passes, create `skills/<area>/<skill>.md`:

1. Copy `skills/_template.md` -> `skills/<area>/<new-skill>.md`.
2. Fill frontmatter (id, name, category, phase, risk, depends_on, provides, triggers, parameters, output).
3. Write commands (with `[risk:ro|info|probe] [mode:auto]` tags).
4. Write analysis, false positives, thresholds, evidence, security.
5. Add entry in `skills/_index.yaml` under `skills:` and optional workflow.
6. Run `python3 scripts/validate_catalog.py`.

## Requirements and verification

- Python 3.10+ + PyYAML (pinned in `requirements.txt`) — report generation/catalog checks
- Bash, OpenSSH, GNU `timeout`, and standard Unix utilities — local SSH wrapper
- An AI coding agent (opencode / Claude Code style) that reads `AGENTS.md`

Skills contain remote command inventories. Individual checks additionally require
the corresponding target utilities and permissions; missing tools are evidence
gaps, not successful checks. No remote packages are installed automatically.

```bash
python scripts/validate_catalog.py
bash -n scripts/ssh_exec.sh scripts/redact.sh scripts/run_id.sh
python -m unittest discover -s tests -v
python scripts/gen_report.py reportes/<run-id>
```

Run report generation only on an existing local evidence directory. Tests use
synthetic inputs and a fake SSH executable; they never connect to a target.
GitHub Actions runs catalog, shell syntax, regression and history secret checks.
There is no measured live-host coverage or cross-distribution certification.

The SSH wrapper resolves environment overrides first, then `config/target.json`,
then defaults. It records redacted command text/stdout/stderr under
`reportes/<run-id>/evidencia/`. A zero wrapper exit means evidence was recorded;
inspect the YAML `exit_code` before treating a command as successful. Reports
show executed skills only when recorded as `executed` in `skills-used.yaml`;
an absent ledger is explicitly unknown.

## Security

- **Heuristic redaction.** `scripts/redact.py` filters common passwords, tokens,
  private keys and connection strings before evidence is written. It cannot
  guarantee detection of every format. Command metadata is redacted too, but
  command arguments and raw output still exist transiently in process memory.
- **Publication boundary.** `config/target.json` and `reportes/` are gitignored,
  not a data-loss prevention system. Review evidence, personal data, hostnames
  and findings before sharing; never commit credentials or real target records.
- **Read-only by default.** Mutations require explicit operator approval per `SAFETY.md`.
- **Completely reusable.** Only `config/target.json` changes between scans. No hardcoded hostnames.
- **No scan history in repo.** All evidence, reports, and scan data go into `reportes/` which is gitignored.

Report HTML escapes target/run/skill metadata and finding content. It renders
supplied evidence and analyst findings; it does not independently validate the
agent's conclusions, perform migrations or implement hardening/rollback.
