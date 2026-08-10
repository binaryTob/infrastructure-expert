# SKILLS.md — Skill System

A **skill** is a self-contained capability the agent can select, validate, and execute. A skill is plain text (`SKILL.md`) — it contains a YAML frontmatter header plus a command inventory and interpretation guidance. There is no executable code in a skill; the agent *reads* the skill and runs the commands through `scripts/ssh_exec.sh` (read-only SSH).

## Directory layout

```
skills/
├── _index.yaml              <- master catalog with dependencies and triggers
├── _schema.yaml             <- formal contract every skill must satisfy
├── _template.md             <- canonical template for creating new skills
├── common/
│   └── helpers.md           <- reusable modules (ssh_run, redact, detect, etc.)
├── discovery/               <- system inventory, systemd (services + resources)
├── resources/               <- CPU, memory, disk, I/O, process, network
├── platform/                <- Docker, Kubernetes, ingress-nginx, Traefik, database
├── security/                <- security posture analysis
├── analysis/                <- configuration, logs, capacity, optimization
├── reliability/             <- HA/SPOF analysis
├── observability/           <- monitoring stack health
├── backup/                  <- backup mechanisms detection
└── migration/               <- A->B migration assessment
```

## SKILL.md schema

```markdown
---
id: <kebab-case-id>
name: <human-readable name>
version: "1.0"
category: <cpu|memory|disk|io|network|...>
phase: <discover|analyze|correlate|optimize|assess>
risk: readonly|advisory
execution_mode: auto|confirm|manual
depends_on:
  - <skill-id>
provides:
  - <evidence-key>
triggers:
  - "PRESENT:<binary>"
  - "CONDITION:<expression>"
false_positives:
  - "FP description"
references:
  - "URL doc"
parameters:
  OUTPUT_DIR:
    type: filepath
    default: "{{RUN_DIR}}/<skill-id>"
    description: "Evidence directory for this skill"
  SSH_TARGET:
    type: string
    required: true
    description: "SSH spec: user@host or alias"
  SAMPLE_INTERVAL:
    type: duration
    default: "30s"
  SAMPLE_COUNT:
    type: integer
    default: 4
output:
  format: json
  schema: output_schema
---

# Skill description

## Objective
What this skill measures and why.

## Commands
### Block 1
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} '<readonly-command>'
```

### Block 2 (conditional)
```bash
# [risk:ro] [mode:auto] [requires:COMPONENT]
ssh {{SSH_TARGET}} '<command>'
```

## Analysis
- Finding A -> conclusion X
- Finding B -> conclusion Y

## Thresholds
| Metric | NORMAL | WATCH | WARNING | CRITICAL |
|--------|--------|-------|---------|----------|
| (%)    | < 50   | 50-70 | 70-85   | > 85     |

## Evidence produced
- `metric.txt` in `{{OUTPUT_DIR}}`

## Security
Read-only. All blocks are L1 or L2.
```

## Skill selection (the agent does this every run)

1. After global discovery, build the inventory of present technologies.
2. For each skill in `_index.yaml`, check `depends_on` and `triggers`.
3. Select skills where prerequisites are satisfied by current evidence.
4. Run `discovery` -> `tests` -> `interpretation` for each selected skill.
5. If a technology is present but has no skill -> **generate one** (per `_template.md`), validate against `_schema.yaml`, run it, persist it.

## Adding / generating a skill

To add manually: create the folder + `SKILL.md` following the schema and `_template.md`. Add an entry in `_index.yaml`.

To generate dynamically during a run, see `WORKFLOW.md` step 6 "dynamic skill generation".

## Anti-patterns (forbidden)

- A skill that only contains `TODO` / placeholder text. Every persisted skill is functional.
- A skill whose commands mutate the host (Level 3) — such steps must instead be proposed under `remediation_template` with an approval gate.
- Hard-coding host/IP/credentials in a skill. A skill is reusable across servers; only `config/target.json` is host-specific.
