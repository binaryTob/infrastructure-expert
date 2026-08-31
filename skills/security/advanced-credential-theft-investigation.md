---
id: "advanced_credential_theft_investigation"
name: "Advanced Credential Theft Investigation — Complete Attack Vector Analysis"
version: "2.0"
category: "security"
phase: "forensic"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
triggers: []
provides:
  - "env_files_complete_inventory"
  - "github_tokens_detected"
  - "ssh_keys_audit"
  - "git_repos_with_secrets"
  - "docker_secrets_exposed"
  - "web_exposed_credentials"
  - "exfiltration_evidence"
  - "attack_timeline"
  - "persistence_mechanisms"
  - "root_cause_hypothesis"
parameters:
  OUTPUT_DIR:
    type: "filepath"
    default: "{{RUN_DIR}}/advanced-credential-theft"
  SSH_TARGET:
    type: "string"
    required: true
  DEPTH:
    type: "string"
    default: "comprehensive"
    description: "Scan depth: quick|comprehensive|exhaustive"
output:
  format: "json"
  schema: "output_schema"
---

# Advanced Credential Theft Investigation

## Objective
Complete forensic analysis to determine HOW credentials (.env files, GitHub push tokens,
SSH keys) were stolen from this server. Goes beyond basic discovery — reconstructs the
attack timeline, identifies the attack vector, and provides root cause analysis.

## Attack Vectors Investigated
1. **Direct file theft** — .env files, .git-credentials, .netrc, SSH private keys
2. **Web exposure** — .env served via HTTP, phpinfo(), config files
3. **Docker leakage** — container env vars, volume mounts, socket exposure
4. **Process memory** — /proc/pid/environ with secrets, open file descriptors
5. **Git history** — tokens in git log, commit messages, remote URLs
6. **Cron/backdoor** — scheduled tasks exfiltrating data
7. **SSH abuse** — agent forwarding, key theft, lateral movement
8. **Log poisoning** — tokens logged in bash_history, auth logs

## Pre-flight
```bash
# [risk:info] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== SYSTEM BASIC INFO ==="; hostname; uname -a; id; echo; echo "=== RUNNING SERVICES ==="; systemctl list-units --type=service --state=running --no-pager | head -20; echo; echo "=== DOCKER STATUS ==="; docker ps --format "{{.Names}}" 2>/dev/null | head -10 || echo "Docker not available"'
```

## Phase 1: Complete .env File Discovery

### 1.1 Find ALL .env files system-wide
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== COMPLETE .ENV INVENTORY ==="; find / -name ".env*" -type f 2>/dev/null | while read f; do echo "FILE: $f"; ls -la --time-style=full-iso "$f" 2>/dev/null; stat --format="  Owner: %U:%G | Perms: %a | Size: %s | Modified: %y | Accessed: %x" "$f" 2>/dev/null; echo; done'
```

### 1.2 Find .env files with content (check if empty or real secrets)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== .ENV FILES WITH CONTENT ==="; find / -name ".env*" -type f -size +0c 2>/dev/null | while read f; do lines=$(wc -l < "$f" 2>/dev/null); size=$(stat -c %s "$f" 2>/dev/null); echo "FILE: $f | Lines: $lines | Size: ${size}B"; done'
```

### 1.3 .env files in git repositories (tracked secrets)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== .ENV FILES IN GIT REPOS ==="; find / -name ".git" -type d 2>/dev/null | while read gitdir; do
  repo=$(dirname "$gitdir")
  env_files=$(find "$repo" -name ".env*" -type f 2>/dev/null)
  if [ -n "$env_files" ]; then
    echo "REPO: $repo"
    echo "$env_files" | while read ef; do
      echo "  .ENV: $ef"
      git -C "$repo" log --oneline --follow -5 -- "$(basename "$ef")" 2>/dev/null | sed "s/^/    LOG: /"
    done
  fi
done'
```

### 1.4 .env files with weak permissions
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== .ENV WITH WEAK PERMISSIONS ==="; find / -name ".env*" -type f \( -perm -004 -o -perm -040 -o -perm -400 \) 2>/dev/null | while read f; do echo "[WEAK] $f"; ls -la "$f" 2>/dev/null; done; echo; echo "=== .ENV IN /tmp /var/tmp /dev/shm ==="; find /tmp /var/tmp /dev/shm -name ".env*" -type f 2>/dev/null'
```

## Phase 2: GitHub Token & Git Credential Detection

### 2.1 Search for GitHub token patterns in ALL files
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== GITHUB TOKEN PATTERNS IN FILES ==="; grep -rlE "ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82}|gho_[a-zA-Z0-9]{36}|ghu_[a-zA-Z0-9]{36}|ghs_[a-zA-Z0-9]{36}|ghr_[a-zA-Z0-9]{36}" /home /root /opt /etc /tmp /var /srv 2>/dev/null | while read f; do echo "[FOUND] $f"; grep -oE "gh[pousr]_[a-zA-Z0-9]{36,82}" "$f" 2>/dev/null | head -3 | sed "s/.*/    TOKEN_TYPE: & (redacted)/"; done'
```

### 2.2 Check .git-credentials and .netrc
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== .git-credentials FILES ==="; find / -name ".git-credentials" -type f 2>/dev/null | while read f; do echo "[CRITICAL] $f"; ls -la "$f" 2>/dev/null; wc -l "$f" 2>/dev/null; done; echo; echo "=== .netrc FILES ==="; find / -name ".netrc" -type f 2>/dev/null | while read f; do echo "[CRITICAL] $f"; ls -la "$f" 2>/dev/null; done; echo; echo "=== .git/config with embedded tokens ==="; find / -name ".git" -type d 2>/dev/null | while read d; do grep -l "url.*@github.com\|token\|credential" "$d/config" 2>/dev/null | while read c; do echo "[CRITICAL] $c"; grep -E "url|token|credential|password" "$c" 2>/dev/null; done; done'
```

### 2.3 SSH keys audit (for git push)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== SSH PRIVATE KEYS ==="; for d in /root/.ssh /home/*/.ssh; do [ -d "$d" ] || continue; echo "DIR: $d"; for f in "$d"/id_*; do [ -f "$f" ] && [ "${f%.pub}" != "$f" ] && echo "KEY: $f" && ssh-keygen -lf "$f" 2>/dev/null && ls -la "$f" 2>/dev/null; done; echo "authorized_keys:"; cat "$d/authorized_keys" 2>/dev/null | wc -l; echo "keys"; done; echo; echo "=== AGENT FORWARDING CONFIG ==="; grep -r "ForwardAgent" /root/.ssh/config /home/*/.ssh/config 2>/dev/null'
```

### 2.4 Bash history with tokens/credentials
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== BASH HISTORY CREDENTIAL PATTERNS ==="; for h in /root/.bash_history /home/*/.bash_history; do [ -f "$h" ] || continue; echo "--- $h ---"; echo "Lines with tokens:"; grep -ncE "ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82}|TOKEN|SECRET|PASSWORD|API_KEY|DATABASE_URL|GIT_CREDENTIALS|PRIVATE_KEY|curl.*-H.*Authorization|git clone.*https://.*@|git push.*origin|ssh.*-[LRD]" "$h" 2>/dev/null; echo "Git commands:"; grep -nE "git push|git clone|git pull|git fetch|git remote" "$h" 2>/dev/null | tail -15; echo "Curl/wget:"; grep -nE "curl|wget" "$h" 2>/dev/null | tail -10; echo; done'
```

## Phase 3: Docker Secrets Exposure

### 3.1 Container environment variables with secrets
```bash
# [risk:ro] [mode:auto] [requires:docker]
ssh {{SSH_TARGET}} 'echo "=== DOCKER CONTAINER SECRETS ==="; docker ps --format "{{.ID}} {{.Names}}" 2>/dev/null | while read id name; do echo "CONTAINER: $name ($id)"; docker inspect "$id" --format "{{range .Config.Env}}{{.}}{{\"\n\"}}{{end}}" 2>/dev/null | grep -iE "KEY|SECRET|TOKEN|PASSWORD|DATABASE_URL|API|GITHUB|GIT|PASS|CREDENTIAL|AUTH|PRIVATE" | sed "s/=.*/=<REDACTED>/"; echo "MOUNTS:"; docker inspect "$id" --format "{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}} (RW={{.RW}}){{\"\n\"}}{{end}}" 2>/dev/null | grep -iE "env|secret|credential|password|key|git"; echo; done'
```

### 3.2 Docker socket exposure
```bash
# [risk:ro] [mode:auto] [requires:docker]
ssh {{SSH_TARGET}} 'echo "=== DOCKER SOCKET EXPOSURE ==="; docker ps -q 2>/dev/null | while read id; do name=$(docker inspect "$id" --format "{{.Name}}" 2>/dev/null); docker inspect "$id" --format "{{range .Mounts}}{{.Source}}{{\"\n\"}}{{end}}" 2>/dev/null | grep -q "docker.sock" && echo "[CRITICAL] docker.sock mounted in: $name ($id)"; done; echo; echo "=== PRIVILEGED CONTAINERS ==="; docker ps -q 2>/dev/null | while read id; do priv=$(docker inspect "$id" --format "{{.HostConfig.Privileged}}" 2>/dev/null); name=$(docker inspect "$id" --format "{{.Name}}" 2>/dev/null); [ "$priv" = "true" ] && echo "[CRITICAL] PRIVILEGED: $name ($id)"; done'
```

## Phase 4: Web Exposure Analysis

### 4.1 HTTP probes for .env files
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== HTTP PROBES FOR .ENV ==="; for port in 80 443 8080 8443 3000 8000 5000 8888 9000; do for path in "/.env" "/.env.local" "/.env.production" "/.env.backup" "/.env.development" "/env"; do code=$(curl -sk -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port$path" --max-time 3 2>/dev/null); [ "$code" != "404" ] && [ "$code" != "000" ] && [ "$code" != "403" ] && echo "[CRITICAL] port=$port path=$path HTTP=$code"; done; done'
```

### 4.2 Exposed git repositories via HTTP
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== EXPOSED GIT REPOS ==="; for port in 80 443 8080 8443 3000 8000; do for path in "/.git/HEAD" "/.git/config" "/.git/index"; do code=$(curl -sk -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port$path" --max-time 3 2>/dev/null); [ "$code" = "200" ] && echo "[HIGH] Git exposed on port $port: $path"; done; done'
```

## Phase 5: Filesystem Forensics

### 5.1 Recently modified credential files
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== CREDENTIAL FILE MODIFICATIONS ==="; echo "--- Last 24 hours ---"; find / \( -name ".env*" -o -name ".git-credentials" -o -name ".netrc" -o -name "id_rsa" -o -name "id_ed25519" -o -name "id_ecdsa" -o -name "authorized_keys" -o -name ".gitconfig" \) -type f -mtime -1 -exec ls -la --time-style=full-iso {} \; 2>/dev/null; echo "--- Last 7 days ---"; find / \( -name ".env*" -o -name ".git-credentials" -o -name ".netrc" -o -name "id_rsa" -o -name "id_ed25519" \) -type f -mtime -7 -exec ls -la --time-style=full-iso {} \; 2>/dev/null'
```

### 5.2 Processes with credential files open
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== PROCESSES WITH SENSITIVE FILES OPEN ==="; for pid in $(ls /proc 2>/dev/null | grep "^[0-9]" | head -500); do if [ -d "/proc/$pid/fd" ] 2>/dev/null; then comm=$(cat /proc/$pid/comm 2>/dev/null); user=$(stat -c %U /proc/$pid 2>/dev/null); fds=$(ls -la /proc/$pid/fd 2>/dev/null); echo "$fds" | grep -qiE "\.env|\.git-credentials|\.netrc|id_rsa|id_ed25519|authorized_keys|\.git/config" && echo "PID $pid ($comm, user=$user) has credential file open"; fi; done'
```

### 5.3 Deleted files still open
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== DELETED FILES STILL OPEN ==="; find /proc/*/fd -lname "*(deleted)*" 2>/dev/null | head -30 | while read fd; do pid=$(echo "$fd" | cut -d/ -f3); target=$(readlink "$fd" 2>/dev/null); comm=$(cat /proc/$pid/comm 2>/dev/null); echo "PID $pid ($comm) -> $target"; done'
```

## Phase 6: Audit Log Analysis

### 6.1 Authentication events
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== AUTH FAILURES LAST 30 DAYS ==="; journalctl --since "30 days ago" 2>/dev/null | grep -iE "failed|invalid|authentication failure" | wc -l; echo; echo "=== TOP ATTACKER IPs ==="; journalctl --since "30 days ago" 2>/dev/null | grep -iE "failed password|authentication failure" | sed -n "s/.*from \([0-9.]*\).*/\1/p" | sort | uniq -c | sort -rn | head -10; echo; echo "=== SUCCESSFUL LOGINS ==="; last -20 2>/dev/null; echo; echo "=== SSH AUTH EVENTS ==="; journalctl -u ssh --since "7 days ago" 2>/dev/null | grep -iE "accepted|failed|invalid" | tail -20'
```

### 6.2 Post-exploitation indicators
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== POST-EXPLOITATION INDICATORS ==="; echo "--- Files in /tmp last 7 days ---"; find /tmp /var/tmp /dev/shm -type f -mtime -7 2>/dev/null | head -20; echo "--- Recently modified system binaries ---"; find /usr/bin /usr/sbin /bin /sbin -mtime -30 2>/dev/null | head -10; echo "--- Suspicious authorized_keys ---"; find / -name "authorized_keys" -mtime -30 2>/dev/null | head -10; echo "--- Processes from /tmp ---"; ps aux | grep -E "/tmp/|/var/tmp/" | grep -v grep'
```

## Phase 7: Network Exfiltration Detection

### 7.1 Outbound connections
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== ESTABLISHED OUTBOUND CONNECTIONS ==="; ss -tnp state established | grep -vE "127\.0\.0\.1|::1" | awk "{print \$5,\$6}" | sort -u; echo; echo "=== PROCESSES WITH NETWORK TOOLS ==="; ps aux | grep -iE "curl|wget|nc |ncat|socat|ssh.*-[LR]|rsync.*@|scp " | grep -v grep'
```

### 7.2 Cron jobs with network commands
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== CRON JOBS WITH NETWORK COMMANDS ==="; for f in /etc/crontab /etc/cron.d/* /var/spool/cron/crontabs/*; do [ -f "$f" ] || continue; echo "--- $f ---"; grep -nE "curl|wget|nc |ncat|ssh|scp|rsync|python.*urllib" "$f" 2>/dev/null; done'
```

## Phase 8: Attack Vector Correlation

After collecting all evidence, perform cross-analysis:

### 8.1 Timeline reconstruction
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== ATTACK TIMELINE RECONSTRUCTION ==="; echo "--- Credential file access timeline ---"; find / \( -name ".env*" -o -name ".git-credentials" -o -name "id_rsa" -o -name "id_ed25519" \) -type f -printf "%T+ %p\n" 2>/dev/null | sort | tail -30; echo; echo "--- Recent git operations ---"; find / -name "HEAD" -path "*/.git/*" -mtime -7 -type f 2>/dev/null | while read h; do repo=$(dirname "$(dirname "$h")"); echo "REPO: $repo (modified: $(stat -c %y "$h" 2>/dev/null))"; done'
```

## Analysis & Interpretation

### Severity Matrix for Findings
| Finding | Severity | Confidence | Attack Vector |
|---------|----------|------------|---------------|
| .git-credentials file exists with content | CRITICAL | HIGH | Direct file theft |
| GitHub PAT found in any file | CRITICAL | HIGH | Token exposure |
| .env world-readable in web directory | CRITICAL | HIGH | Web exposure |
| docker.sock mounted in container | CRITICAL | HIGH | Container escape |
| Token in bash_history | CRITICAL | HIGH | Log exposure |
| SSH key without passphrase | HIGH | MEDIUM | Key theft |
| .env backup files (.env.bak, .env.old) | HIGH | MEDIUM | Backup exposure |
| Container with host network mode | MEDIUM | HIGH | Network sniffing |
| Cron job with curl to unknown endpoint | HIGH | MEDIUM | Data exfiltration |
| Process with credential files open | MEDIUM | MEDIUM | Memory access |

### Root Cause Analysis Framework
1. **Initial Access**: How did attacker get in? (SSH brute force, vulnerability, insider)
2. **Privilege Escalation**: Did they escalate? (sudo, container escape, kernel exploit)
3. **Credential Harvesting**: What did they access? (.env, git, SSH keys)
4. **Exfiltration**: How did data leave? (git push, curl, SCP, DNS tunnel)
5. **Persistence**: Did they leave backdoors? (cron, authorized_keys, systemd)

## Evidence Produced
- `env-inventory.yml` — complete .env file inventory
- `github-tokens.yml` — GitHub token detection results
- `git-credentials.yml` — git credential files found
- `ssh-keys-audit.yml` — SSH key inventory
- `docker-secrets.yml` — container secret exposure
- `web-exposure.yml` — HTTP probe results
- `filesystem-timeline.yml` — file access timeline
- `audit-events.yml` — authentication and audit events
- `network-connections.yml` — outbound connection analysis
- `attack-hypothesis.yml` — root cause hypothesis

## False Positives
- .env.example or .env.template (check content for actual values)
- Legitimate monitoring tools accessing /proc
- CI/CD runners with expected credential access
- Backup scripts reading .env files
- Development environments with intentional exposure

## Security
Read-only. NEVER output actual secret values. Only report:
- File paths and permissions
- Token types (ghp_*, gho_*, etc.) and presence
- Process names and PIDs
- IP addresses and timestamps
All output must pass through `scripts/redact.sh`.
