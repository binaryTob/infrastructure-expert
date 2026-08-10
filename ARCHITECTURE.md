# ARCHITECTURE.md — How the framework fits together

The "agent" is **not** a background daemon. It is an opencode (Claude Code-style) session executing instructions in `AGENTS.md` against files in `workflows/` and `skills/`, touching the remote host **only** through `scripts/ssh_exec.sh`. Everything is plain text + small shell scripts, so a future run is reproducible from the evidence on disk.

## Layers

```
┌──────────────────────────────────────────────────────────────┐
│  AGENT SESSION (opencode)                                     │
│  reads: AGENTS.md, workflows/*, skills/*, lib/*               │
│  reasons: OBSERVE->UNDERSTAND->HYPOTHESIZE->TEST->VERIFY->... │
└───────────────┬──────────────────────────────────────────────┘
                │ executes via Bash tool
                ▼
┌──────────────────────────────────────────────────────────────┐
│  scripts/ssh_exec.sh   — READ-ONLY SSH abstraction            │
│  * host/port/user from config/target.json                    │
│  * records every command + output as reportes/<run-id>/*.yml │
│  * pipes output through scripts/redact.sh                    │
│  * enforces a mutability blocklist (Level 3 gate)             │
└───────────────┬──────────────────────────────────────────────┘
                │ ssh
                ▼
┌──────────────────────────────────────────────────────────────┐
│  REMOTE HOST  (e.g. Ubuntu 24.04 + k3s + ingress + ...)       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  OUTPUTS                                                      │
│  reportes/<run-id>/*.yml   — reproducible evidence            │
│  reportes/<run-id>/*.html  — human report (offline)           │
│  skills/<area>/<tech>/     — persisted new skills             │
└──────────────────────────────────────────────────────────────┘
```

## Components

- **`AGENTS.md`** — the operating contract (safety, hard rules, loop).
- **`workflows/infrastructure-audit.md`** — the autonomous reasoning loop entry point. Modes: full, quick, discovery, container, security.
- **`workflows/server-resource-analysis.md`** — resource/performance-focused workflow.
- **`skills/<area>/<skill>.md`** — a capability: `applies_when` + `discovery` + `tests` + `interpretation` + `remediation_template`. Plain text; the agent reads and executes, never code.
- **`skills/_index.yaml`** — master catalog of all 22 skills with dependencies and triggers.
- **`skills/_schema.yaml`** — formal contract every skill must satisfy.
- **`skills/common/helpers.md`** — reusable modules: ssh_run, redact, detect, snapshot_loop, finding, safety_guard.
- **`scripts/ssh_exec.sh`** — the only sanctioned way to reach the host. Reads `config/target.json`, runs a command, captures exit/stdout/stderr, writes a redacted evidence YAML.
- **`scripts/redact.py`** / **`redact.sh`** — secret-value redaction (keys, tokens, K8s secrets, conn strings).
- **`scripts/run_id.sh`** — derives a stable `<YYYYMMDD-HHMM>-<hostslug>` run id and creates `reportes/<run-id>/`.
- **`lib/severity.md`** — severity matrix + confidence rules, used by the risk engine.
- **`scripts/gen_report.py`** — reads `reportes/<run-id>/` + emitted `findings.yaml` + optional `migration.yaml` and renders `reportes/<run-id>/informe-<run-id>.html` (offline, self-contained).

## Data flow

```
config/target.json
        │
        ▼
ssh_exec.sh -> reportes/<run-id>/evidencia/*.yml  (redacted)
        │
        ▼
agent reads evidence -> builds inventory + graph
        │
        ▼
agent selects skills (applies_when/triggers) -> may generate new SKILL.md
        │
        ▼
agent runs more skills via ssh_exec.sh -> more evidence
        │
        ▼
agent writes:  reportes/<run-id>/findings.yaml
              reportes/<run-id>/inventory.yaml
              reportes/<run-id>/graph.yaml
              (optional) reportes/<run-id>/migration.yaml
        │
        ▼
gen_report.py -> reportes/<run-id>/informe-<run-id>.html
        │
        ▼
agent prints executive summary to console
```

## Why this design

- **Evidence first**: no finding exists without a stored, redacted evidence record. Reproducible, auditable.
- **No daemon**: an opencode session is the runtime; skills are data. Nothing to install beyond `ssh` + `python3`.
- **Safety by construction**: `ssh_exec.sh` carries a mutability blocklist; the session context also forbids Level 3.
- **Reusable across hosts**: only `config/target.json` changes. Skills are host-agnostic command inventories.
- **Dynamic skill generation**: the loop detects "present tech, no skill" and writes a new `SKILL.md`, persisted for next time.
- **Read-only by default**: all 22 skills are L1 or L2. Zero destructive actions without approval.
