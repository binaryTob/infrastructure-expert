# ARCHITECTURE.md — How the framework fits together

The "agent" is **not** a background daemon. It is an opencode (Claude Code‑style) session executing instructions in `AGENTS.md` against files in `workflows/` and `skills/`, touching the remote host **only** through `scripts/ssh_exec.sh`. Everything is plain text + small shell scripts, so a future run is reproducible from the evidence on disk.

## Layers

```
┌──────────────────────────────────────────────────────────────┐
│  AGENT SESSION (opencode)                                     │
│  reads: AGENTS.md, workflows/*, skills/*, lib/*               │
│  reasons: OBSERVE→UNDERSTAND→HYPOTHESIZE→TEST→VERIFY→…       │
└───────────────┬──────────────────────────────────────────────┘
                │ executes via Bash tool
                ▼
┌──────────────────────────────────────────────────────────────┐
│  scripts/ssh_exec.sh   — READ-ONLY SSH abstraction            │
│  • host/port/user from config/target.json                    │
│  • records every command + output as evidence/<run-id>/*.yml │
│  • pipes output through scripts/redact.sh                    │
│  • enforces a mutability blocklist (Level 3 gate)             │
└───────────────┬──────────────────────────────────────────────┘
                │ ssh
                ▼
┌──────────────────────────────────────────────────────────────┐
│  REMOTE HOST  (e.g. Ubuntu 24.04 + k3s + ingress + …)          │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  OUTPUTS                                                      │
│  evidence/<run-id>/*.yml   — reproducible evidence            │
│  reports/*.html             — human report (offline)          │
│  skills/<area>/<tech>/     — persisted new skills             │
└──────────────────────────────────────────────────────────────┘
```

## Components

- **`AGENTS.md`** — the operating contract (safety, hard rules, loop).
- **`workflows/infrastructure-audit.md`** — the autonomous reasoning loop entry point. Modes: DISCOVERY, SECURITY, MIGRATION, PERFORMANCE, INCIDENT, FULL.
- **`skills/<area>/<tech>/SKILL.md`** — a capability: `applies_when` + `discovery` + `tests` + `interpretation` + `remediation_template`. Plain text; the agent reads and executes, never code.
- **`scripts/ssh_exec.sh`** — the only sanctioned way to reach the host. Reads `config/target.json`, runs a command, captures exit/stdout/stderr, writes a redacted evidence YAML.
- **`scripts/redact.sh`** — secret‑value redaction (keys, tokens, K8s secrets, conn strings). Reused by `ssh_exec.sh` and by the report generator.
- **`scripts/run_id.sh`** — derives a stable `<timestamp>-<hostslug>` run id and creates `evidence/<run-id>/`.
- **`lib/severity.md`** — severity matrix + confidence rules, used by the risk engine.
- **`lib/compat/*.md`** — compatibility tables (e.g. source → target technology feature matrix), used by the migration engine.
- **`scripts/gen_report.py`** — reads `evidence/<run-id>/` + an emitted `findings.yaml` + an optional `migration.yaml` and renders `reports/infrastructure-audit-<ts>.html` (offline, self‑contained).

## Data flow

```
config/target.json
        │
        ▼
ssh_exec.sh ─► evidence/<run-id>/NN_category.yml  (redacted)
        │
        ▼
agent reads evidence → builds inventory + graph
        │
        ▼
agent selects skills (applies_when)  ─► may generate new SKILL.md
        │
        ▼
agent runs more skills via ssh_exec.sh ─► more evidence
        │
        ▼
agent writes:  evidence/<run-id>/findings.yaml
              evidence/<run-id>/inventory.yaml
              evidence/<run-id>/graph.yaml
              (optional) evidence/<run-id>/migration.yaml
        │
        ▼
gen_report.py ─► reports/infrastructure-audit-<ts>.html
        │
        ▼
agent prints executive summary to console
```

## Why this design

- **Evidence first**: no finding exists without a stored, redacted evidence record. Reproducible, auditable.
- **No daemon**: an opencode session is the runtime; skills are data. Nothing to install on the operator's machine beyond `ssh` + `python3`.
- **Safety by construction**: `ssh_exec.sh` carries a mutability blocklist; the session context also forbids Level 3. Two layers, same intent.
- **Reusable across hosts**: only `config/target.json` changes. Skills are host‑agnostic command inventories.
- **Dynamic skill generation**: the loop detects "present tech, no skill" and writes a new `SKILL.md`, persisted for next time.