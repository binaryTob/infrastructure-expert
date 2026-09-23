# SKILLS.md — Skill System

A **skill** is a reusable, self-contained capability the agent can select, validate, and execute. A skill is plain text (`*.md`) containing YAML frontmatter, a command inventory and interpretation guidance. Product discovery alone does not justify a skill. The agent reads command blocks as remote payload descriptions and executes them only through `scripts/ssh_exec.sh`.

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
3. Add transitive dependencies, topologically order the result, then select skills whose triggers match current evidence.
4. Run each selected skill once, reusing fresh evidence owned by earlier skills.
5. Diagnose-only skills require a symptom or anomaly marker; technology presence alone selects posture/inventory analysis only.
6. If no existing skill answers a concrete question, use a bounded ad-hoc check first. Persist a new skill only if it passes the full creation gate in `WORKFLOW.md`.

## Adding a skill

Before adding a skill, document why generic evidence and an ad-hoc check are insufficient, the expected reuse across targets/runs, and the existing skills reviewed for overlap. A one-product inventory check, one-off incident command or convenience wrapper is not a skill.

When the gate passes, create `skills/<area>/<skill>.md` following `_template.md`, add it to `_index.yaml`, validate both files, and execute it once through `scripts/ssh_exec.sh`. `_index.yaml` is authoritative for dependencies, triggers, phase, risk and provided evidence.

Trigger semantics:
- `depends_on` entries are AND and must complete first.
- Multiple `triggers` are OR.
- Empty `triggers` means unconditional only within a workflow's candidate set.
- `PRESENT:` and `SERVICE:` select posture analysis; `SYMPTOM:` and `CONDITION:` gate diagnostic escalation.
- `[requires:...]` applies to one command block and is evaluated immediately before execution.

## Anti-patterns (forbidden)

- A skill that only contains `TODO` / placeholder text. Every persisted skill is functional.
- A skill whose commands mutate the host (Level 3) — such steps must instead be proposed under `remediation_template` with an approval gate.
- Hard-coding host/IP/credentials in a skill. A skill is reusable across servers; only `config/target.json` is host-specific.
- A skill created only because a new product or process name was discovered.
- A skill that repeats commands or evidence already owned by another skill instead of consuming that evidence.
- Direct `ssh`, `tee` or redirection of unredacted remote output during execution; all remote commands use `scripts/ssh_exec.sh`.
