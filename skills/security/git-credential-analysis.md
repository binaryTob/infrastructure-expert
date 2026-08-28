---
id: "git_credential_analysis"
name: "Git Credential Theft Analysis"
version: "1.0"
category: "security"
phase: "forensic"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
triggers: []
provides: ["git_repos", "git_credentials", "ssh_keys", "github_tokens"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/git-credentials" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Git Credential Theft Analysis

## Objective
Investigate all vectors for Git/GitHub credential theft: .git-credentials files,
.git/config with embedded tokens, SSH keys for git, credential helpers, bash history
with tokens, and agent forwarding abuse.

## Commands

### 1. Find all git repositories
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== ALL GIT REPOS ==="; find / -name ".git" -type d 2>/dev/null | head -30'
```

### 2. Audit .git/config for embedded credentials
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'find / -name ".git" -type d 2>/dev/null | while read gitdir; do
  repo=$(dirname "$gitdir")
  echo "=== REPO: $repo ==="
  echo "--- config ---"
  cat "$gitdir/config" 2>/dev/null | grep -iE "url|credential|token|pass|user"
  echo "--- .git-credentials ---"
  [ -f "$gitdir/.git-credentials" ] && echo "[FOUND] $gitdir/.git-credentials" && wc -l "$gitdir/.git-credentials" 2>/dev/null
  echo "--- .netrc ---"
  [ -f "$gitdir/.netrc" ] && echo "[FOUND] $gitdir/.netrc"
  echo "--- credentials file ---"
  [ -f "$gitdir/credentials" ] && echo "[FOUND] $gitdir/credentials"
  echo
done'
```

### 3. Find .git-credentials anywhere on the system
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== .git-credentials FILES ==="; find / -name ".git-credentials" -type f 2>/dev/null; echo; echo "=== .netrc FILES ==="; find / -name ".netrc" -type f 2>/dev/null; echo; echo "=== credentials FILES ==="; find / -path "*/.git/credentials" -type f 2>/dev/null'
```

### 4. Git credential helper configuration
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== GLOBAL GIT CONFIG ==="; cat ~/.gitconfig 2>/dev/null; echo; echo "=== GIT CREDENTIAL HELPERS ==="; git config --global --list 2>/dev/null | grep -iE "credential|helper|user"; echo; echo "=== PER-USER GIT CONFIG ==="; for h in /home/*; do [ -f "$h/.gitconfig" ] && echo "--- $h/.gitconfig ---" && cat "$h/.gitconfig" 2>/dev/null | grep -iE "credential|helper|token|user"; done'
```

### 5. SSH keys audit (used for git push)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== SSH KEYS ==="; for d in /root/.ssh /home/*/.ssh; do
  [ -d "$d" ] && echo "--- $d ---" && ls -la "$d/" 2>/dev/null
  for f in "$d"/id_*; do
    [ -f "$f" ] && [ "${f%.pub}" != "$f" ] && echo "KEY: $f" && ssh-keygen -lf "$f" 2>/dev/null
  done
done'
```

### 6. SSH keys permissions audit
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== SSH KEY PERMISSIONS ==="; for d in /root/.ssh /home/*/.ssh; do
  [ -d "$d" ] && echo "DIR: $d ($(stat -c %a "$d" 2>/dev/null))" && for f in "$d"/id_* "$d"/authorized_keys "$d"/config; do
    [ -f "$f" ] && echo "  $(basename "$f"): $(stat -c "%a %U:%G" "$f" 2>/dev/null)"
  done
done'
```

### 7. Agent forwarding configuration
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== AGENT FORWARDING ==="; grep -r "ForwardAgent" /root/.ssh/config /home/*/.ssh/config 2>/dev/null; echo; echo "=== SSH CONFIG FILES ==="; for f in /root/.ssh/config /home/*/.ssh/config; do [ -f "$f" ] && echo "--- $f ---" && cat "$f" 2>/dev/null; done'
```

### 8. GitHub tokens in bash history
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== BASH HISTORY WITH TOKENS ==="; grep -lE "ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82}|gho_[a-zA-Z0-9]{36}|ghu_[a-zA-Z0-9]{36}|ghs_[a-zA-Z0-9]{36}|GH_TOKEN|GITHUB_TOKEN|git push|git clone.*@" /root/.bash_history /home/*/.bash_history 2>/dev/null; echo; echo "=== RECENT GIT COMMANDS IN HISTORY ==="; grep -iE "git push|git clone|git pull|git fetch" /root/.bash_history /home/*/.bash_history 2>/dev/null | tail -20'
```

### 9. GitHub token patterns in any file
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== GITHUB TOKEN PATTERNS ==="; grep -rlE "ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82}|gho_[a-zA-Z0-9]{36}|ghu_[a-zA-Z0-9]{36}|ghs_[a-zA-Z0-9]{36}" /home /root /opt /etc /tmp 2>/dev/null | head -20'
```

### 10. .git/config permissions (world-readable repos)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== GIT CONFIG PERMISSIONS ==="; find / -name ".git" -type d 2>/dev/null | while read d; do
  config="$d/config"
  [ -f "$config" ] && ls -la "$config" 2>/dev/null
done'
```

### 11. Recent git activity (repos accessed recently)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== RECENTLY MODIFIED GIT REPOS ==="; find / -name "HEAD" -path "*/.git/*" -mtime -30 -type f 2>/dev/null | while read head; do
  repo=$(dirname "$(dirname "$head")")
  echo "REPO: $repo (modified: $(stat -c %y "$head" 2>/dev/null))"
done'
```

### 12. Git remote URLs (check for token in URL)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'find / -name ".git" -type d 2>/dev/null | while read gitdir; do
  repo=$(dirname "$gitdir")
  remote=$(git -C "$repo" remote -v 2>/dev/null | head -2)
  [ -n "$remote" ] && echo "REPO: $repo" && echo "$remote" && echo
done'
```

## Analysis

### Severity mapping
| Finding | Severity | Confidence |
|---------|----------|------------|
| .git-credentials file exists | CRITICAL | HIGH |
| .git/config with `url = https://TOKEN@github.com/...` | CRITICAL | HIGH |
| .netrc with github.com credentials | CRITICAL | HIGH |
| GitHub PAT (ghp_*) found in any file | CRITICAL | HIGH |
| Token in bash_history | CRITICAL | HIGH |
| SSH key without passphrase (no -N) | HIGH | MEDIUM |
| ForwardAgent yes in SSH config | HIGH | HIGH |
| .git/config world-readable with credentials | HIGH | HIGH |
| SSH key permissions > 600 | MEDIUM | HIGH |
| .ssh directory permissions > 700 | MEDIUM | HIGH |

### Attack vectors
1. **Direct file theft:** Attacker reads .git-credentials or .git/config with token
2. **SSH key theft:** Attacker copies private SSH key from compromised server
3. **Agent forwarding abuse:** Attacker uses SSH agent forwarding to sign with victim's key
4. **History exposure:** Token was used in a command and remains in bash_history
5. **Memory dump:** Process memory containing credentials (requires /proc access)

### Correlation
- Cross-reference with `credential_exposure_analysis` for .env in git repos
- Cross-reference with `filesystem_forensics` for access timeline to .git-credentials
- Cross-reference with `network_exfiltration` for git push/pull patterns

## Evidence
- `git-repos.yml` — inventory of all git repos
- `git-credentials-found.yml` — credential files found
- `ssh-keys-audit.yml` — SSH key inventory + permissions
- `github-tokens-found.yml` — GitHub token patterns found
- `git-config-permissions.yml` — .git/config permissions

## False Positives
- `ghp_` pattern in documentation/changelogs (check if it's a real token vs example)
- .git-credentials in a CI/CD runner (expected, but verify it's not in a public repo)
- SSH key for automated deployment (intentional, but verify it's not pushed to public repos)

## Security
Read-only. NEVER output actual token/key values. Only report:
- File path and permissions
- Token type (ghp_*, gho_*, etc.) and length
- Presence/absence (boolean)
All output must pass through `scripts/redact.sh`.
