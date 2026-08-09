# SKILLS.md — Skill System

A **skill** is a self‑contained capability the agent can select, validate, and execute. A skill is plain text (`SKILL.md`) — it contains a YAML frontmatter header plus a command inventory and interpretation guidance. There is no executable code in a skill; the agent *reads* the skill and runs the commands through `scripts/ssh_exec.sh` (read‑only SSH).

## Directory layout

```
skills/
└── <area>/            # discovery, linux, networking, security, docker,
                       # waf, systemd, storage, databases, observability,
                       # performance, backup, migration, hardening, reporting
    └── <tech>/        # optional; e.g. skills/networking/cilium/
        └── SKILL.md
```

An `<area>` may contain a `SKILL.md` directly (e.g. `skills/networking/SKILL.md` for general network analysis) and/or nested technology folders (`skills/networking/traefik/`).

## SKILL.md schema

```markdown
---
name: <kebab-case-name>            # unique, e.g. ingress-nginx-analysis
area: <area>                       # from the layout above
description: <one line>
purpose: <what the agent achieves with this skill>
safety: L1 | L2                    # default safety level of its commands
prerequisites:                     # what must be true for it to apply
  - <e.g. "kubectl context exists">
applies_when:                      # command(s) whose success implies this skill applies
  - "command -v kubectl"
inputs:                            # what the agent must already have discovered
  - <e.g. "kubeconfig location">
discovery:                         # read-only commands to gather evidence
  - "<command>"
tests:                             # level-2 non-destructive tests
  - "<command>"
evidence_artifacts:                # list of evidence files this skill produces
  - "<evidence yaml basename>"
interpretation:                    # how to turn evidence -> findings
  - <rule of thumb, thresholds, FP guidance>
risk_model: <how severity is assigned>
remediation_template: |
  WHAT:
  WHY:
  HOW:
  RISK:
  PRIORITY:
  VALIDATION:
  ROLLBACK:
references:
  - <official docs / advisories>
---

# <Skill name> — body

Narrative guidance: how the agent runs `discovery` + `tests`, what to look for,
how to avoid false positives, and how to phrase findings.
```

## Skill selection (the agent does this every run)

1. After global discovery, build the inventory of present technologies.
2. For each `<area>/<tech>`, check `applies_when`.
3. Select skills where prerequisites are satisfied by current evidence.
4. Run `discovery` → `tests` → `interpretation` for each selected skill.
5. If a technology is present but has no skill → **generate one** (`applies_when` + `discovery` + `tests` + `interpretation`), validate it, run it, persist it to `skills/<area>/<tech>/SKILL.md`.

## Adding / generating a skill

To add manually: create the folder + `SKILL.md` following the schema above. To generate dynamically during a run, see `WORKFLOW.md` step "dynamic skill generation".

## Anti‑patterns (forbidden)

- A skill that only contains `TODO` / placeholder text. Every persisted skill is functional (`discovery` + `tests` + `interpretation` populated).
- A skill whose `tests` mutate the host (Level 3) — such steps must instead be proposed under `remediation_template` with an approval gate.
- Hard‑coding host/IP/credentials in a skill. A skill is reusable across servers; only `config/target.json` is host‑specific.