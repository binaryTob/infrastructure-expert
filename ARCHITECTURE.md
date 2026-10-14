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
│  skills/<area>/<skill>.md  — curated reusable capabilities    │
└──────────────────────────────────────────────────────────────┘
```

## Components

- **`AGENTS.md`** — the operating contract (safety, hard rules, loop).
- **`workflows/infrastructure-audit.md`** — the autonomous reasoning loop entry point. Modes: full, quick, discovery, container, security.
- **`workflows/server-resource-analysis.md`** — resource/performance-focused workflow.
- **`skills/<area>/<skill>.md`** — a capability: `applies_when` + `discovery` + `tests` + `interpretation` + `remediation_template`. Plain text; the agent reads and executes, never code.
- **`skills/_index.yaml`** — master catalog of all skills with dependencies and triggers.
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
agent selects skills (dependencies + triggers) -> bounded ad-hoc checks if needed
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
- **Layered operational guardrails**: `ssh_exec.sh` carries a best-effort regex mutability blocklist; the session contract also forbids automatic Level 3. Neither is an OS sandbox. The local operator/agent is trusted, and remote privileges must be restricted independently.
- **Reusable across hosts**: only `config/target.json` changes. Skills are host-agnostic command inventories.
- **Curated skill growth**: unsupported technology is handled first by generic capabilities and bounded ad-hoc checks. A new skill is persisted only when a distinct, reusable capability passes the creation gate in `WORKFLOW.md`.
- **Read-only by default**: all skills are L1 or L2. Zero destructive actions without approval.

## Verification and evidence boundaries

The deterministic helpers are tested offline with synthetic data and a fake SSH
executable. `validate_catalog.py` verifies catalog/frontmatter agreement and
dependency/workflow consistency; it does not execute skill commands.

SSH key/timeouts honor environment > target configuration > defaults. Evidence
metadata accepts safe basenames/categories and L1/L2 levels. Command text and
both output streams are heuristically redacted before persistence; evidence is
private by default. Raw input still exists in process memory, and SSH capture
currently buffers output there. Bound each remote query to avoid excessive output.

Inventory, graph, findings and the executed-skill ledger are produced by the
agent session. The report renderer consumes these files; it cannot prove their
claims. Missing skill execution records remain unknown rather than treating the
catalog as executed. Keyword-matching journal events is not proof of an attack.
