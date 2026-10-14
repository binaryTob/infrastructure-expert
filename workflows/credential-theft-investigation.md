# Workflow: Credential Theft Investigation

Forensic investigation of credential theft (.env / GitHub push keys).
Uses discovery, security and forensic catalog skills to reconstruct the attack vector.

## Minimum input

| Variable | Required | Default | Description |
|----------|-----------|---------|-------------|
| `SSH_TARGET` | yes | — | `user@host` or a configured SSH alias |
| `MODE` | no | `forensic` | `forensic` (default for this workflow) |

## Execution diagram

```
PHASE 1: DISCOVERY (existing skills)
  │
  ├── system_inventory        → OS, kernel, users, services, network triage
  ├── systemd_analysis        → services, timers, restarts
  ├── process_analysis        → all processes, tree, zombies
  └── network_analysis        → interfaces, ports, connections, firewall
  │
  v
PHASE 2: SECURITY BASELINE (existing skills)
  │
  ├── security_analysis       → SSH posture, privileged procs, persistence
  └── ssh_hardening_analysis  → sshd_config, fail2ban, authorized_keys
  │
  v
PHASE 3: CREDENTIAL EXPOSURE (NEW forensic skills — v2.0 ADVANCED)
  │
  └── advanced_credential_theft_investigation  → COMPLETE attack vector analysis
      │
      ├── Phase 3.1: Complete .env Discovery
      │   ├── All .env files system-wide with metadata
      │   ├── .env files in git repos (tracked secrets)
      │   └── .env with weak permissions
      │
      ├── Phase 3.2: GitHub Token & Git Credential Detection
      │   ├── GitHub token patterns in ALL files
      │   ├── .git-credentials and .netrc check
      │   ├── SSH keys audit (for git push)
      │   └── Bash history with tokens/credentials
      │
      ├── Phase 3.3: Docker Secrets Exposure
      │   ├── Container environment variables with secrets
      │   └── Docker socket exposure
      │
      ├── Phase 3.4: Web Exposure Analysis
      │   ├── HTTP probes for .env files
      │   └── Exposed git repositories via HTTP
      │
      ├── Phase 3.5: Filesystem Forensics
      │   ├── Recently modified credential files
      │   ├── Processes with credential files open
      │   └── Deleted files still open
      │
      ├── Phase 3.6: Audit Log Analysis
      │   ├── Authentication events
      │   └── Post-exploitation indicators
      │
      ├── Phase 3.7: Network Exfiltration Detection
      │   ├── Outbound connections
      │   └── Cron jobs with network commands
      │
      └── Phase 3.8: Attack Vector Correlation
          └── Timeline reconstruction
  │
  v
PHASE 4: FORENSIC TIMELINE (NEW forensic skills)
  │
  ├── filesystem_forensics    → file access timeline, open files, deleted artifacts
  └── audit_logs_forensics    → auth logs, auditd, post-exploitation indicators
  │
  v
PHASE 5: ATTACK SURFACE (NEW forensic skills)
  │
  ├── web_secret_exposure     → HTTP probes for .env, config files, phpinfo (conditional)
  └── network_exfiltration    → outbound connections, curl in cron, SSH tunnels
  │
  v
PHASE 6: PLATFORM (existing conditional skills)
  │
  ├── docker_analysis         → container inventory (if Docker present)
  ├── web_server_analysis     → nginx/apache config (if web server present)
  ├── tls_certificate_analysis→ cert audit (if web server present)
  ├── database_analysis       → DB connections, config (if DB present)
  └── log_analysis            → journal errors, OOM, disk errors
  │
  v
PHASE 7: RESOURCES (existing skills)
  │
  ├── cpu_analysis
  ├── memory_analysis
  ├── disk_analysis
  └── io_analysis
  │
  v
PHASE 8: ANALYSIS & CORRELATION (existing skills)
  │
  ├── configuration_analysis  → sysctl, limits, server config
  ├── reliability_analysis    → SPOF, restart policies
  └── observability_analysis  → monitoring, log rotation
  │
  v
PHASE 9: FINDINGS GENERATION
  │
  ├── Cross-reference all evidence
  ├── Build attack timeline hypothesis
  ├── Generate findings with severity + confidence
  └── Write findings.yaml
  │
  v
PHASE 10: REPORT
  │
  ├── Generate forensic HTML report
  └── Print executive summary
```

## Per-phase execution rules

### Phases 1–2 (Discovery + Security Baseline)
- Run all unconditional skills.
- They establish inventory and security posture.

### Phases 3–5 (Forensic Skills)
- Run the forensic skills, subject to their triggers.
- `docker_secrets_analysis`: only when Docker is present (automatic trigger).
- `web_secret_exposure`: only when a web server is present (automatic trigger).
- Run the remaining unconditional skills.

### Phase 6 (Platform)
- Run only if the component was detected in Phase 1.
- Follow `_index.yaml` triggers.

### Phases 7–8 (Resources + Analysis)
- Run all listed skills: they provide low-cost context.

## Hard rules (inherited from infrastructure-audit.md)

1. **Read-only.** Do not modify the server.
2. **Evidence first.** Every claim needs stored evidence.
3. **Fact vs hypothesis.** Label every claim.
4. **Secret redaction.** Never include secret values in evidence/reports.
5. **No assumptions.** Discover; never assume.

## Output

Report directory: `reportes/<run-id>/`
- `reportes/<run-id>/evidencia/` — per-command YAML records
- `reportes/<run-id>/findings/` — findings
- `reportes/<run-id>/findings.yaml` — structured findings
- `reportes/<run-id>/inventory.yaml` — inventory
- `reportes/<run-id>/informe-forense-<run-id>.html` — forensic HTML report

## Safety levels (see SAFETY.md)

| Level | Name | Scope | Default |
|-------|------|-------|---------|
| 1 | OBSERVE | Read-only commands | Always on |
| 2 | TEST | Non-destructive tests (HTTP probes) | On by default |
| 3 | CHANGE | Mutating actions | Off — requires explicit approval |

## Technology without a dedicated skill

Technology presence alone does not justify a new skill. Reuse generic forensic
capabilities first and run bounded L1/L2 ad-hoc checks when evidence is missing.
Persist a skill only if it meets every necessity, reuse, non-overlap, stability
and validation criterion in `WORKFLOW.md`.
