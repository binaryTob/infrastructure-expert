---
id: "audit_logs_forensics"
name: "Audit Logs Forensics Analysis"
version: "1.0"
category: "security"
phase: "forensic"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
triggers: []
provides: ["audit_events", "auth_log_analysis", "post_exploitation"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/audit-logs-forensics" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Audit Logs Forensics Analysis

## Objective
Analyze system audit and authentication logs to reconstruct the attack timeline:
failed login attempts, successful logins, file access events, process execution,
and post-exploitation indicators.

## Commands

### 1. Authentication failures (brute force evidence)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== AUTH FAILURES LAST 30 DAYS ==="; journalctl --since "30 days ago" 2>/dev/null | grep -iE "failed|invalid|authentication failure" | wc -l; echo; echo "=== TOP ATTACKER IPs ==="; journalctl --since "30 days ago" 2>/dev/null | grep -iE "failed password|authentication failure" | sed -n "s/.*from \([0-9.]*\).*/\1/p" | sort | uniq -c | sort -rn | head -15; echo; echo "=== FAILED LOGINS BY DAY ==="; journalctl --since "30 days ago" 2>/dev/null | grep -iE "failed password" | awk "{print \$1,\$2,\$3}" | sort | uniq -c | sort -rn | head -15'
```

### 2. Successful logins
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== RECENT SUCCESSFUL LOGINS ==="; last -30 2>/dev/null; echo; echo "=== CURRENTLY LOGGED IN ==="; who; echo; echo "=== LOGIN HISTORY ==="; lastb -30 2>/dev/null | head -20'
```

### 3. SSH authentication events
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== SSH AUTH EVENTS LAST 7 DAYS ==="; journalctl -u ssh --since "7 days ago" 2>/dev/null | grep -iE "accepted|failed|invalid|error" | tail -40; echo; echo "=== SSHD LOG PATTERNS ==="; grep -iE "sshd.*accepted|sshd.*failed|sshd.*invalid" /var/log/auth.log 2>/dev/null | tail -30; grep -iE "sshd.*accepted|sshd.*failed|sshd.*invalid" /var/log/secure 2>/dev/null | tail -30'
```

### 4. Privilege escalation events
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== SUDO USAGE ==="; grep -i "sudo" /var/log/auth.log 2>/dev/null | tail -20; grep -i "sudo" /var/log/syslog 2>/dev/null | tail -20; echo; echo "=== SU USAGE ==="; grep "su:" /var/log/auth.log 2>/dev/null | tail -10'
```

### 5. File access audit (if auditd configured)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== AUDITD STATUS ==="; systemctl is-active auditd 2>/dev/null; echo; echo "=== AUDIT RULES ==="; auditctl -l 2>/dev/null; echo; echo "=== RECENT FILE ACCESS EVENTS ==="; ausearch -k "file_access" --start today 2>/dev/null | tail -20; echo; echo "=== CREDENTIAL FILE ACCESS ==="; ausearch -f "/.env" 2>/dev/null | tail -10; ausearch -f ".git-credentials" 2>/dev/null | tail -10; ausearch -f ".netrc" 2>/dev/null | tail -10; ausearch -f "id_rsa" 2>/dev/null | tail -10; ausearch -f "id_ed25519" 2>/dev/null | tail -10'
```

### 6. Process execution audit
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== RECENT PROCESS EXECUTION ==="; ausearch -k "exec" --start today 2>/dev/null | tail -30; echo; echo "=== PROCESSES FROM /tmp ==="; ps aux | grep -E "/tmp/|/var/tmp/" | grep -v grep; echo; echo "=== PROCESSES WITH DELETED BINARIES ==="; ls -la /proc/*/exe 2>/dev/null | grep "(deleted)" | head -10'
```

### 7. System logs for anomalies
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== SYSLOG ANOMALIES LAST 7 DAYS ==="; journalctl --since "7 days ago" -p warning 2>/dev/null | tail -30; echo; echo "=== KERNEL MESSAGES ==="; dmesg -T 2>/dev/null | grep -iE "error|fail|segfault|oom|killed" | tail -20'
```

### 8. User creation/modification events
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== USER/MODIFICATION EVENTS ==="; grep -iE "useradd|usermod|userdel|groupadd|passwd" /var/log/auth.log 2>/dev/null | tail -20; echo; echo "=== CURRENT USERS WITH SHELL ==="; grep -E "/sh$" /etc/passwd; echo; echo "=== USERS WITH NO PASSWORD FIELD ==="; awk -F: "(\$2 == \"\" || \$2 == \"!\") {print \$1}" /etc/passwd 2>/dev/null'
```

### 9. Cron job modifications
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== CRON MODIFICATIONS ==="; grep -iE "cron.*modified|crontab" /var/log/syslog 2>/dev/null | tail -20; echo; echo "=== CRON JOB OWNERSHIP ==="; ls -la /var/spool/cron/crontabs/ 2>/dev/null; echo; echo "=== CRON.D FILES ==="; ls -la /etc/cron.d/ 2>/dev/null'
```

### 10. Post-exploitation indicators
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== POST-EXPLOITATION INDICATORS ==="; echo "--- Files created in /tmp in last 7 days ---"; find /tmp /var/tmp /dev/shm -type f -mtime -7 2>/dev/null | head -20; echo "--- Suspicious shell scripts ---"; find / -maxdepth 4 -name "*.sh" -mtime -30 -not -path "*/node_modules/*" -not -path "*/.cache/*" -not -path "/usr/*" 2>/dev/null | head -15; echo "--- Recently modified system binaries ---"; find /usr/bin /usr/sbin /bin /sbin -mtime -30 2>/dev/null | head -10; echo "--- Unauthorized SSH authorized_keys ---"; find / -name "authorized_keys" -mtime -30 2>/dev/null | head -10'
```

### 11. Log rotation and retention
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== LOG DISK USAGE ==="; du -sh /var/log /var/log/journal 2>/dev/null; echo; echo "=== LOGROTATE CONFIG ==="; cat /etc/logrotate.conf 2>/dev/null | head -20; echo; echo "=== RECENTLY ROTATED LOGS ==="; ls -la /var/log/*.gz 2>/dev/null | tail -10; echo; echo "=== JOURNAL SIZE ==="; journalctl --disk-usage 2>/dev/null'
```

## Analysis

### Severity mapping
| Finding | Severity | Confidence |
|---------|----------|------------|
| >1000 failed SSH attempts in 30 days | HIGH | HIGH |
| Successful login from attacker IP | CRITICAL | HIGH |
| Sudo usage from non-admin user | HIGH | HIGH |
| Process running from /tmp | HIGH | HIGH |
| Deleted binary still in use | HIGH | HIGH |
| Authorized_keys modified in last 30 days | OBSERVATION | HIGH |
| User created in last 30 days | OBSERVATION | HIGH |
| Audit rules targeting credential files | INFO (good) | HIGH |
| Log files deleted/truncated | HIGH | HIGH |
| Journal size > 1GB | MEDIUM | HIGH |

### Timeline reconstruction
For each finding, build a timeline:
1. **Initial access** — first successful login or exploitation
2. **Privilege escalation** — sudo, su, or exploit
3. **Credential harvesting** — access to .env, .git-credentials
4. **Lateral movement** — SSH to other systems, git push
5. **Exfiltration** — data leaving the server
6. **Persistence** — cron jobs, authorized_keys, systemd units

### Correlation
- Cross-reference with `filesystem_forensics` for file access timestamps
- Cross-reference with `network_exfiltration` for simultaneous network activity
- Cross-reference with `credential_exposure_analysis` for what was accessible
- Cross-reference with `git_credential_analysis` for git-specific events

## Evidence
- `auth-failures.yml` — brute force evidence
- `successful-logins.yml` — login history
- `ssh-auth-events.yml` — SSH authentication events
- `audit-events.yml` — auditd events (if available)
- `post-exploitation.yml` — indicators of compromise
- `log-retention.yml` — log health

## False Positives
- Failed logins from known monitoring IPs (check against infrastructure inventory)
- Legitimate cron modifications by admin (check timestamp against maintenance windows)
- Files in /tmp from package managers (check ownership and content)
- User creation during planned deployments

## Security
Read-only. Never output actual passwords or credential values from logs.
Only report: IP addresses, timestamps, process names, file paths, usernames.
All output must pass through `scripts/redact.sh`.
