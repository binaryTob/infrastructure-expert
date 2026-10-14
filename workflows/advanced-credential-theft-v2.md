# Workflow: Advanced Credential Theft Investigation v2.0

Advanced forensic workflow to investigate how .env files or GitHub push keys were
stolen. Combines discovery and platform skills with the advanced credential-theft
investigation capability to analyze attack vectors.

## Objective
Reconstruct the attack vector:
1. How the attacker gained access.
2. Which credentials were accessed.
3. How data was exfiltrated.
4. Whether persistence mechanisms were left behind.

## Execution diagram

```
PHASE 1: DISCOVERY (existing skills)
  │
  ├── system_inventory        → OS, kernel, users, services, network
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
PHASE 3: ADVANCED CREDENTIAL THEFT INVESTIGATION (NEW v2.0)
  │
  └── advanced_credential_theft_investigation
      │
      ├── Phase 3.1: Complete .env Discovery
      │   ├── All .env files system-wide
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
PHASE 4: PLATFORM (existing conditional skills)
  │
  ├── docker_analysis         → container inventory (if Docker present)
  ├── web_server_analysis     → nginx/apache config (if web server present)
  ├── tls_certificate_analysis→ cert audit (if web server present)
  ├── database_analysis       → DB connections, config (if DB present)
  └── log_analysis            → journal errors, OOM, disk errors
  │
  v
PHASE 5: RESOURCES (existing skills)
  │
  ├── cpu_analysis
  ├── memory_analysis
  ├── disk_analysis
  └── io_analysis
  │
  v
PHASE 6: ANALYSIS & CORRELATION (existing skills)
  │
  ├── configuration_analysis  → sysctl, limits, server config
  ├── reliability_analysis    → SPOF, restart policies
  └── observability_analysis  → monitoring, log rotation
  │
  v
PHASE 7: FINDINGS GENERATION
  │
  ├── Cross-reference all evidence from Phase 3
  ├── Build attack timeline hypothesis
  ├── Determine root cause (initial access vector)
  ├── Generate findings with severity + confidence
  └── Write findings.yaml
  │
  v
PHASE 8: REPORT
  │
  ├── Generate forensic HTML report
  └── Print executive summary with:
      ├── Attack vector hypothesis
      ├── Credentials compromised
      ├── Exfiltration method
      └── Recommended remediations
```

## Per-phase execution rules

### Phases 1–2 (Discovery + Security Baseline)
- Run all unconditional skills.
- They establish inventory and security posture.

### Phase 3 (Advanced Credential Theft Investigation)
- Run `advanced_credential_theft_investigation`.
- This skill is self-contained and covers its internal phases.
- It does not require additional investigative skills, but can complement them.

### Phase 4 (Platform)
- Run only if the component was detected in Phase 1.
- Follow `_index.yaml` triggers.

### Phases 5–6 (Resources + Analysis)
- Run all listed skills: they provide low-cost context.

## Hard rules

1. **Read-only.** Do not modify the server.
2. **Evidence first.** Every claim needs stored evidence.
3. **Fact vs hypothesis.** Label every claim.
4. **Secret redaction.** Never include secret values in evidence/reports.
5. **No assumptions.** Discover; never assume.

## Output

Report directory: `reportes/<run-id>/`
- `reportes/<run-id>/evidencia/` — per-command YAML records
- `reportes/<run-id>/advanced-credential-theft/` — primary skill evidence
- `reportes/<run-id>/findings/` — findings
- `reportes/<run-id>/findings.yaml` — structured findings
- `reportes/<run-id>/inventory.yaml` — inventory
- `reportes/<run-id>/informe-forense-<run-id>.html` — forensic HTML report

## Safety levels

| Level | Name | Scope | Default |
|-------|------|-------|---------|
| 1 | OBSERVE | Read-only commands | Always on |
| 2 | TEST | Non-destructive tests (HTTP probes) | On by default |
| 3 | CHANGE | Mutating actions | Off — requires explicit approval |

## Technology without a dedicated skill

Do not create a skill for every detected product. Reuse evidence and generic
forensic capabilities; cover concrete gaps with bounded L1/L2 ad-hoc checks.
Persist a new skill only after the complete gate in `WORKFLOW.md` passes.
