# Infrastructure Expert — Autonomous Infrastructure Analysis Framework

> **OBSERVE -> UNDERSTAND -> HYPOTHESIZE -> TEST -> VERIFY -> DOCUMENT -> RECOMMEND**

This project is an **autonomous infrastructure expert agent**. It connects to a remote Linux server over SSH, discovers its real architecture from evidence (never from assumptions), runs non-destructive tests, evaluates security / reliability / performance, assesses migration feasibility, and produces a professional offline HTML report.

The "agent" is the opencode (Claude Code-style) session itself, driven by this `AGENTS.md` plus the files in `workflows/` and `skills/`. There is no separate daemon. The skills are plain-text instructions + read-only command inventories that the agent executes through the SSH abstraction layer (`scripts/`). Evidence is captured on disk in `reportes/` so every finding is reproducible.

## Safety contract (read first)

- **Level 1 — OBSERVE**: read-only commands. Always on.
- **Level 2 — TEST**: non-destructive tests (e.g. `curl`, `kubectl get`, TLS inspection). On by default.
- **Level 3 — CHANGE**: any mutating command. **Off by default.** Requires explicit user approval for each action.

The agent must **never** automatically: restart/stop services, edit config, delete files, install packages, run `kubectl delete/apply`, change firewall rules, or run destructive payloads. If a destructive action is the only way forward -> STOP, DOCUMENT, REQUEST APPROVAL.

See `SAFETY.md`.

## Hard rules (the agent enforces these every run)

1. **No assumptions.** Distribution, init system, container runtime, orchestrator, ingress, databases, WAF, firewall, cloud provider — all must be *discovered*, never assumed.
2. **Evidence first.** No assertion about the server ("has X", "is exposed") without a stored evidence record in `reportes/<run-id>/`.
3. **Fact vs Hypothesis.** Label every claim as `FACT`, `OBSERVATION`, `HYPOTHESIS`, `RISK`, or `RECOMMENDATION`. Never present a hypothesis as a fact.
4. **Low false-positive rate.** An anomalous-looking port/process/config is NOT a finding until: evidence + context + exposure + impact are all evaluated.
5. **Secret redaction.** Secrets are *detected and reported as metadata only* (location, type, risk). Values are redacted before any report/evidence output.
6. **Migration rule.** A migration objective does NOT start with the migration plan. It starts with fully understanding the current state.
7. **Skill economy.** Discovering a technology is never, by itself, a reason to create a skill. Reuse existing capabilities and bounded ad-hoc checks first. Persist only capabilities that are necessary, non-overlapping, host-agnostic, and expected to be reused across targets or runs.
8. **Single execution path.** Every remote command is executed through `scripts/ssh_exec.sh`. Command blocks in skills describe remote payloads; never run their literal `ssh` examples directly or write raw output to evidence.
9. **English narrative output.** Write analysis, findings, recommendations and executive summaries in English. Preserve captured target output verbatim after redaction; do not translate evidence or rename existing storage paths.

## How to run an audit (operator)

1. Put SSH target + objective + optional context into `config/target.json` (or pass inline). **Never commit credentials.**
2. From the repo root, ask the agent: *"Run the infrastructure audit workflow on the configured target."* (or a specific mode: `full`, `quick`, `discovery`, `container`, `security`).
3. The agent follows `workflows/infrastructure-audit.md`, executing skills, writing evidence into `reportes/<run-id>/`, and producing `reportes/<run-id>/informe-<run-id>.html`.
4. The agent prints an executive summary to the console and the report path.

## How to run a diagnosis (operator)

If you are reporting a **symptom** (not asking for a full audit) — e.g. "the site returns 502",
"the disk is full", "a container keeps restarting" — the agent follows
`workflows/incident-triage.md` and reads `lib/diagnosis.yaml` (symptom -> hypotheses ->
evidence -> skills). It runs only the skills needed to find the root cause and the
remediation, and it never fixes anything without Level 3 approval.

## How to run an audit (the agent — read this before starting)

When invoked, follow this loop (full spec in `workflows/infrastructure-audit.md`):

```
CONNECT (verify, no assumptions about OS)
DISCOVER (skills/discovery — broad, cheap, read-only)
CLASSIFY -> BUILD INVENTORY -> BUILD GRAPH
SELECT SKILLS (only those matching what was discovered)
RUN ANALYSIS (selected skills, non-destructive tests)
FIND ANOMALIES -> CREATE HYPOTHESES -> RUN TESTS -> VERIFY
UPDATE GRAPH -> REASSESS (select more skills or bounded ad-hoc checks only when new evidence requires them)
GENERATE FINDINGS (FACT/OBSERVATION/HYPOTHESIS/RISK/RECOMMENDATION + severity + confidence)
GENERATE REMEDIATIONS (WHAT/WHY/HOW/RISK/PRIORITY/VALIDATION/ROLLBACK)
[if migration objective] MIGRATION ANALYSIS
GENERATE HTML REPORT -> PRINT EXECUTIVE SUMMARY
```

**Skill creation is an exception, not a discovery action.** An unsupported technology is recorded in inventory, then handled with existing generic skills or a bounded L1/L2 ad-hoc check. A new skill may be persisted only if all creation-gate criteria in `WORKFLOW.md` are satisfied. Product presence alone, a one-off command, or convenience does not pass the gate.

## Repository layout

```
infrastructure-expert/
├── AGENTS.md              <- operating contract for the AI agent
├── README.md              <- project overview for humans
├── ARCHITECTURE.md        <- how the framework fits together
├── WORKFLOW.md            <- the autonomous reasoning loop
├── SKILLS.md              <- skill schema + how to create skills
├── REPORTING.md           <- report structure + redaction rules
├── SAFETY.md              <- safety levels + forbidden actions
├── .gitignore             <- excludes config/target.json, reportes/
├── config/                <- target.json (gitignored), target.example.json
├── scripts/               <- SSH wrapper, redaction, report generator
├── lib/                   <- shared helpers (severity matrix, symptom->diagnosis map)
├── skills/                <- reusable capabilities grouped by area
│   ├── _index.yaml        <- master catalog
│   ├── _schema.yaml       <- skill contract
│   ├── _template.md       <- canonical template
│   ├── common/            <- reusable helpers
│   ├── discovery/         <- system inventory, systemd (services + resources)
│   ├── resources/         <- CPU, memory, disk, I/O, process, network
│   ├── platform/          <- Docker, K8s, ingress-nginx, Traefik, database, web server, TLS
│   ├── security/          <- security posture analysis
│   ├── analysis/          <- configuration, logs, capacity, optimization, http health
│   ├── reliability/       <- HA/SPOF analysis
│   ├── observability/     <- monitoring stack health
│   ├── backup/            <- backup mechanisms detection
│   └── migration/         <- A->B migration assessment
├── workflows/             <- entry points: audit (by mode) + incident triage
├── templates/             <- report templates
└── reportes/              <- scan data + reports (gitignored)
```

## Constraints respected

- No credentials are stored in the repo. `reportes/`, `config/target.json` are gitignored.
- Read-only on the host unless Level 3 is explicitly approved.
- Completely reusable across any Linux server — only `config/target.json` changes.
