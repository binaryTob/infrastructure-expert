---
id: "filesystem_forensics"
name: "Filesystem Forensics & Access Timeline"
version: "1.0"
category: "security"
phase: "forensic"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
triggers: []
provides: ["file_timeline", "proc_open_files", "deleted_files", "bash_history"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/filesystem-forensics" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Filesystem Forensics & Access Timeline

## Objective
Reconstruct WHO accessed WHAT credential files and WHEN. Build a forensic timeline
of access to .env, .git-credentials, SSH keys, and other sensitive files. Detect
deleted-but-open files, suspicious processes, and post-exploitation artifacts.

## Commands

### 1. Recently modified credential files
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== CREDENTIAL FILES MODIFIED LAST 30 DAYS ==="; find / \( -name ".env*" -o -name ".git-credentials" -o -name ".netrc" -o -name "id_rsa" -o -name "id_ed25519" -o -name "id_ecdsa" -o -name "authorized_keys" -o -name ".gitconfig" \) -type f -mtime -30 -exec ls -la --time-style=full-iso {} \; 2>/dev/null; echo; echo "=== MODIFIED LAST 24H ==="; find / \( -name ".env*" -o -name ".git-credentials" -o -name ".netrc" -o -name "id_rsa" -o -name "id_ed25519" \) -type f -mtime -1 -exec ls -la --time-style=full-iso {} \; 2>/dev/null'
```

### 2. Stat on credential files (access/modification/change times)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== DETAILED TIMESTAMPS ==="; find / \( -name ".env*" -o -name ".git-credentials" -o -name ".netrc" -o -name "id_rsa" -o -name "id_ed25519" -o -name "authorized_keys" \) -type f -exec stat --format="FILE: %n | Size: %s | Access: %x | Modify: %y | Change: %z | Owner: %U:%G | Perms: %a" {} \; 2>/dev/null'
```

### 3. Linux audit logs (if auditd running)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== AUDITD STATUS ==="; systemctl is-active auditd 2>/dev/null; echo; echo "=== AUDIT RULES ==="; auditctl -l 2>/dev/null | head -30; echo; echo "=== RECENT AUDIT EVENTS FOR CREDENTIALS ==="; ausearch -f "/.env" 2>/dev/null | tail -30; echo; ausearch -f ".git-credentials" 2>/dev/null | tail -20; echo; ausearch -f ".netrc" 2>/dev/null | tail -20; echo; ausearch -f "id_rsa" 2>/dev/null | tail -20; echo; ausearch -f "id_ed25519" 2>/dev/null | tail -20'
```

### 4. Processes with credential files open
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== PROCESSES WITH SENSITIVE FILES OPEN ==="; for pid in $(ls /proc 2>/dev/null | grep "^[0-9]" | head -300); do
  if [ -d "/proc/$pid/fd" ] 2>/dev/null; then
    comm=$(cat /proc/$pid/comm 2>/dev/null)
    user=$(stat -c %U /proc/$pid 2>/dev/null)
    fds=$(ls -la /proc/$pid/fd 2>/dev/null)
    echo "$fds" | grep -qiE "\.env|\.git-credentials|\.netrc|id_rsa|id_ed25519|authorized_keys|\.git/config" && echo "PID $pid ($comm, user=$user) has credential file open"
  fi
done'
```

### 5. Deleted files still open by processes
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== DELETED FILES STILL OPEN ==="; find /proc/*/fd -lname "*(deleted)*" 2>/dev/null | head -50 | while read fd; do
  pid=$(echo "$fd" | cut -d/ -f3)
  target=$(readlink "$fd" 2>/dev/null)
  comm=$(cat /proc/$pid/comm 2>/dev/null)
  echo "PID $pid ($comm) -> $target"
done'
```

### 6. /proc/<pid>/environ for suspicious processes
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== PROCESSES WITH INTERESTING ENV VARS ==="; for pid in $(ls /proc 2>/dev/null | grep "^[0-9]" | head -300); do
  comm=$(cat /proc/$pid/comm 2>/dev/null)
  if echo "$comm" | grep -qiE "python|node|ruby|php|java|curl|wget|git|sh|bash|perl"; then
    env_content=$(cat /proc/$pid/environ 2>/dev/null | tr "\0" "\n" 2>/dev/null)
    env_size=$(echo "$env_content" | wc -c)
    if [ "$env_size" -gt 200 ]; then
      echo "PID $pid ($comm) - environ size: ${env_size} bytes"
      echo "$env_content" | grep -iE "TOKEN|SECRET|KEY|PASSWORD|DATABASE_URL|GITHUB" | head -5
      echo "---"
    fi
  fi
done'
```

### 7. Bash history analysis for credential-related commands
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== BASH HISTORY CREDENTIAL ANALYSIS ==="; for h in /root/.bash_history /home/*/.bash_history; do
  [ -f "$h" ] || continue
  echo "--- $h ---"
  echo "Total lines: $(wc -l < "$h")"
  echo "Commands with tokens:"
  grep -ncE "ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82}|TOKEN|SECRET|PASSWORD|API_KEY|curl.*-H.*Authorization|git clone.*https://.*@|git push" "$h" 2>/dev/null
  echo "Git operations:"
  grep -nE "git push|git clone|git pull|git fetch" "$h" 2>/dev/null | tail -10
  echo "Curl/wget to external:"
  grep -nE "curl|wget" "$h" 2>/dev/null | tail -10
  echo "SSH/SCP/RSYNC:"
  grep -nE "ssh |scp |rsync " "$h" 2>/dev/null | tail -10
  echo
done'
```

### 8. Recently created files in suspicious locations
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== RECENT FILES IN /tmp ==="; find /tmp /var/tmp /dev/shm -type f -mtime -7 2>/dev/null | xargs ls -la --time-style=full-iso 2>/dev/null | sort -k6,7 | tail -30; echo; echo "=== RECENT SCRIPTS IN UNUSUAL LOCATIONS ==="; find / -maxdepth 4 \( -name "*.sh" -o -name "*.py" -o -name "*.pl" -o -name "*.rb" \) -mtime -30 -not -path "*/node_modules/*" -not -path "*/.cache/*" -not -path "/usr/*" -not -path "/snap/*" 2>/dev/null | head -20'
```

### 9. File integrity indicators
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== SUID/SGID FILES (non-standard) ==="; find / -perm -4000 -type f 2>/dev/null | grep -vE "/usr/bin/|/usr/lib/|/bin/|/sbin/|/usr/libexec/" | head -15; echo; echo "=== WORLD-WRITABLE FILES IN SENSITIVE DIRS ==="; find /etc /root /home -perm -002 -type f 2>/dev/null | head -15; echo; echo "=== RECENTLY CREATED FILES IN /etc ==="; find /etc -type f -mtime -30 2>/dev/null | head -20'
```

### 10. Inotify/monitoring watches
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== INOTIFYWATCH / MONITORING PROCESSES ==="; ps aux | grep -iE "inotify|audit|fswatch|entr" | grep -v grep; echo; echo "=== FANOTIFY/INOTIFY KERNEL SUPPORT ==="; cat /proc/filesystems 2>/dev/null | grep -iE "inotify|fanotify"'
```

## Analysis

### Timeline reconstruction
For each credential file found, build:
1. **Creation time** (birth/change time)
2. **Last modification** (content change)
3. **Last access** (read — if atime enabled)
4. **Current permissions** (who can read)
5. **Process association** (which PID has it open)

### Severity mapping
| Finding | Severity | Confidence |
|---------|----------|------------|
| Credential file accessed by non-root process | HIGH | MEDIUM |
| Credential file modified in last 24h | OBSERVATION | HIGH |
| Deleted .env still open by process | HIGH | HIGH |
| Bash history contains token patterns | CRITICAL | HIGH |
| Post-exploitation scripts in /tmp | HIGH | HIGH |
| Suspicious env vars in running process | HIGH | MEDIUM |
| SUID/SGID non-standard binary | MEDIUM | MEDIUM |
| Audit rules targeting credential files | INFO (good) | HIGH |

### Correlation
- Cross-reference with `credential_exposure_analysis` for file locations
- Cross-reference with `git_credential_analysis` for git-specific access
- Cross-reference with `audit_logs_forensics` for system-level audit events
- Cross-reference with `network_exfiltration` for simultaneous network activity

## Evidence
- `file-timeline.yml` — timestamp data for all credential files
- `proc-open-files.yml` — processes with credential files open
- `deleted-files.yml` — deleted but open files
- `bash-history-analysis.yml` — credential-related commands in history
- `suspicious-files.yml` — post-exploitation indicators

## False Positives
- Backup scripts that legitimately read .env (check process name and user)
- Monitoring tools (node_exporter, etc.) reading /proc — not credential-specific
- Build processes (npm, yarn) reading .env during compilation
- Cron jobs for deployment that legitimately access credentials

## Security
Read-only. Never output actual secret values from /proc/<pid>/environ.
Only report: PID, process name, user, environment variable NAMES (not values).
All output must pass through `scripts/redact.sh`.
