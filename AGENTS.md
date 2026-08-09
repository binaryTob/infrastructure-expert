# Infrastructure Expert — Autonomous Infrastructure Analysis Framework

> **OBSERVE → UNDERSTAND → HYPOTHESIZE → TEST → VERIFY → DOCUMENT → RECOMMEND**

This project is an **autonomous infrastructure expert agent**. It connects to a remote Linux server over SSH, discovers its real architecture from evidence (never from assumptions), runs non‑destructive tests, evaluates security / reliability / performance, assesses migration feasibility, and produces a professional offline HTML report.

## What this is

The "agent" is the opencode (Claude Code‑style) session itself, driven by this `AGENTS.md` plus the files in `workflows/` and `skills/`. There is no separate daemon. The skills are plain‑text instructions + read‑only command inventories that the agent executes through the SSH abstraction layer (`scripts/`). Evidence is captured on disk so every finding is reproducible.

## Safety contract (read first)

- **Level 1 — OBSERVE**: read‑only commands. Always on.
- **Level 2 — TEST**: non‑destructive tests (e.g. `curl`, `kubectl get`, TLS inspection). On by default.
- **Level 3 — CHANGE**: any mutating command. **Off by default.** Requires explicit user approval for each action.

The agent must **never** automatically: restart/stop services, edit config, delete files, install packages, run `kubectl delete/apply`, change firewall rules, or run destructive payloads. If a destructive action is the only way forward → STOP, DOCUMENT, REQUEST APPROVAL.

See `SAFETY.md`.

## Hard rules (the agent enforces these every run)

1. **No assumptions.** Distribution, init system, container runtime, orchestrator, ingress, databases, WAF, firewall, cloud provider — all must be *discovered*, never assumed.
2. **Evidence first.** No assertion about the server ("has X", "is exposed") without a stored evidence record in `evidence/`.
3. **Fact vs Hypothesis.** Label every claim as `FACT`, `OBSERVATION`, `HYPOTHESIS`, `RISK`, or `RECOMMENDATION`. Never present a hypothesis as a fact.
4. **Low false‑positive rate.** An anomalous‑looking port/process/config is NOT a finding until: evidence + context + exposure + impact are all evaluated.
5. **Secret redaction.** Secrets are *detected and reported as metadata only* (location, type, risk). Values are redacted before any report/evidence output.
6. **Migration rule.** A migration objective does NOT start with the migration plan. It starts with fully understanding the current state. Technology migration is never assumed trivial.

## How to run an audit (operator)

1. Put SSH target + objective + optional context into `config/target.json` (or pass inline). **Never commit credentials.** `config/target.example.json` shows the shape; for this repo the private key already lives in `~/.ssh/id_ed25519`.
2. From the repo root, ask the agent: *"Run the infrastructure audit workflow on the configured target."* (or a specific mode: `DISCOVERY`, `SECURITY`, `MIGRATION`, `PERFORMANCE`, `INCIDENT`, `FULL`).
3. The agent follows `workflows/infrastructure-audit.md`, executing skills, writing evidence into `evidence/<run-id>/`, and producing `reports/infrastructure-audit-<timestamp>.html`.
4. The agent prints an executive summary to the console and the report path.

## How to run an audit (the agent — read this before starting)

When invoked, follow this loop (full spec in `workflows/infrastructure-audit.md`):

```
CONNECT (verify, no assumptions about OS)
DISCOVER (skills/discovery — broad, cheap, read-only)
CLASSIFY → BUILD INVENTORY → BUILD GRAPH
SELECT SKILLS (only those matching what was discovered)
RUN ANALYSIS (selected skills, non-destructive tests)
FIND ANOMALIES → CREATE HYPOTHESES → RUN TESTS → VERIFY
UPDATE GRAPH → REASSESS (may select more skills; may generate new skills)
GENERATE FINDINGS (FACT/OBSERVATION/HYPOTHESIS/RISK/RECOMMENDATION + severity + confidence)
GENERATE REMEDIATIONS (WHAT/WHY/HOW/RISK/PRIORITY/VALIDATION/ROLLBACK)
[if migration objective] MIGRATION ANALYSIS (current state → deps → feature inventory → compat matrix → gaps → risks → phases → validation → rollback)
GENERATE HTML REPORT → PRINT EXECUTIVE SUMMARY
```

**Dynamic skill generation:** if you discover a technology with no skill directory under `skills/`, create one (`skills/<tech>/SKILL.md` with the schema in `SKILLS.md`), validate it, run it, and persist it. Example: detecting Cilium → create `skills/networking/cilium/`.

## Repository layout

```
infrastructure-expert/
├── AGENTS.md            ← you are reading it; the operating contract
├── README.md            ← project overview for humans
├── ARCHITECTURE.md      ← how the framework fits together
├── WORKFLOW.md          ← the autonomous reasoning loop, narrated
├── SKILLS.md            ← SKILL.md schema + how to add/generate skills
├── REPORTING.md         ← report structure + evidence redaction rules
├── SAFETY.md            ← safety levels + forbidden actions + approval gate
├── config/              ← target.json (gitignored), target.example.json
├── scripts/             ← SSH wrapper, redaction, report generator
├── lib/                 ← shared helpers (severity matrix, compat tables)
├── skills/<area>/       ← one folder per capability; SKILL.md each
├── workflows/           ← entry points per mode
├── evidence/<run-id>/   ← YAML evidence records (gitignored)
└── reports/             ← generated HTML reports
```

## SSH target for this repo

The operator currently wants the agent to analyze one host (config supplied out‑of‑band). The private key is the operator's `~/.ssh/id_ed25519`; **no password is required**. The SSH abstraction (`scripts/ssh_exec.sh`) is the only sanctioned way to touch the host.

## Constraints respected

- No credentials are stored in the repo. `evidence/`, `reports/`, `config/target.json` are gitignored.
- Read‑only on the host unless Level 3 is explicitly approved. The operator of this run stated: *"no corras ningun comando que pueda modificar algo, solo verificar"* — so this run is **Level 1 + Level 2 only.**