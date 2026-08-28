---
id: "credential_exposure_analysis"
name: "Credential & .env Exposure Analysis"
version: "1.0"
category: "security"
phase: "forensic"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
triggers: []
provides: ["env_files", "env_permissions", "web_exposed_env", "credential_files"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/credential-exposure" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Credential & .env Exposure Analysis

## Objective
Find ALL .env files and credential-bearing files on the system. Evaluate permissions,
location (web-accessible, git-tracked, temp dirs), and exposure risk. This is the
PRIMARY skill for credential theft investigation.

## Commands

### 1. Find all .env files
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== ALL .ENV FILES ==="; find / -name ".env*" -type f 2>/dev/null | head -50; echo; echo "=== .ENV IN COMMON LOCATIONS ==="; find /opt /home /root /srv /app /var/www /etc -name ".env*" -type f 2>/dev/null'
```

### 2. Permissions audit for every .env found
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'find / -name ".env*" -type f -exec ls -la --time-style=full-iso {} \; 2>/dev/null'
```

### 3. World-readable .env files
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== WORLD-READABLE .ENV ==="; find / -name ".env*" -type f -perm -004 2>/dev/null; echo; echo "=== GROUP-READABLE .ENV ==="; find / -name ".env*" -type f -perm -040 2>/dev/null'
```

### 4. .env in web-accessible directories
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for webdir in /var/www /srv /opt /home; do find "$webdir" -name ".env*" -type f 2>/dev/null | while read f; do dir=$(dirname "$f"); echo "FILE: $f"; echo "PARENT DIR:"; ls -la "$dir/.." 2>/dev/null | head -5; echo "---"; done; done'
```

### 5. Credential-bearing files (non-.env)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== FILES WITH SECRET KEYWORDS ==="; grep -rlE "DATABASE_URL|API_KEY|SECRET_KEY|AWS_SECRET_ACCESS_KEY|GITHUB_TOKEN|GH_TOKEN|GIT_CREDENTIALS|PRIVATE_KEY|CLIENT_SECRET" /opt /home /root /srv /app /etc 2>/dev/null | head -30'
```

### 6. Config files with embedded credentials
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== YML/YAML WITH SECRETS ==="; grep -rlE "password:|secret:|token:|api_key:|private_key:" /opt /home /root /srv /app --include="*.yml" --include="*.yaml" 2>/dev/null | head -20; echo; echo "=== JSON WITH SECRETS ==="; grep -rlE "\"password\"|\"secret\"|\"token\"|\"api_key\"" /opt /home /root /srv /app --include="*.json" 2>/dev/null | head -20; echo; echo "=== CONF/CFG WITH SECRETS ==="; grep -rlE "password|secret|token|api_key" /opt /home /root /etc --include="*.conf" --include="*.cfg" --include="*.ini" 2>/dev/null | head -20'
```

### 7. Database config files
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== DATABASE CONFIG FILES ==="; find / -maxdepth 5 -name "database.yml" -o -name "database.yaml" -o -name "db.php" -o -name "config.php" -o -name "wp-config.php" -o -name "settings.py" -o -name "ormconfig.*" -o -name "knexfile.*" -o -name "prisma/schema.prisma" 2>/dev/null | head -20; echo; echo "=== .ENV BACKUPS ==="; find / -name ".env.*" -o -name ".env.bak" -o -name ".env.backup" -o -name ".env.old" -o -name "env.local" -o -name "env.production" 2>/dev/null | head -20'
```

### 8. .env in /tmp and unusual locations
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET }} 'echo "=== .ENV IN TEMP ==="; find /tmp /var/tmp /dev/shm -name ".env*" -type f 2>/dev/null; echo; echo "=== .ENV IN UNUSUAL ==="; find / -maxdepth 3 -name ".env" -type f 2>/dev/null; echo; echo "=== HIDDEN .ENV ==="; find / -name ".env" -path "*/.*" -type f 2>/dev/null | head -10'
```

### 9. Recent .env modifications (timeline)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== .ENV MODIFIED LAST 30 DAYS ==="; find / -name ".env*" -type f -mtime -30 -exec ls -la --time-style=full-iso {} \; 2>/dev/null; echo; echo "=== .ENV MODIFIED LAST 7 DAYS ==="; find / -name ".env*" -type f -mtime -7 -exec ls -la --time-style=full-iso {} \; 2>/dev/null'
```

### 10. .env file sizes (detect large/exfiltrated or empty)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'find / -name ".env*" -type f -exec ls -lh {} \; 2>/dev/null'
```

## Analysis

### Severity mapping
| Finding | Severity | Confidence |
|---------|----------|------------|
| .env in web-accessible dir with no protection | CRITICAL | HIGH |
| .env world-readable (644/777) | HIGH | HIGH |
| .env in /tmp or /var/tmp | MEDIUM | HIGH |
| .env with no restriction in Apache/nginx config | CRITICAL | HIGH |
| .env backup files (.env.bak, .env.old) | HIGH | MEDIUM |
| database.yml with plaintext password | HIGH | HIGH |
| .env modified in last 7 days | OBSERVATION | MEDIUM |
| .env > 1MB (possible data dump) | HIGH | MEDIUM |
| .env = 0 bytes (possible wiped) | OBSERVATION | LOW |

### Correlation
- Cross-reference with `git_credential_analysis` for repos containing .env
- Cross-reference with `web_secret_exposure` for HTTP probe results
- Cross-reference with `filesystem_forensics` for access timeline

## Evidence
- `env-files-inventory.yml` — list of all .env files with metadata
- `env-permissions.yml` — permissions audit
- `web-exposed-env.yml` — .env files in web-accessible directories
- `credential-keyword-files.yml` — files containing secret keywords

## False Positives
- .env.example or .env.template files (check content for actual values)
- .env in node_modules/ (dependency, not application secret)
- .env in Docker image layers (pre-built, may not contain real secrets)

## Security
Read-only. Never cat the actual content of .env files (values are secrets).
Only report metadata: path, permissions, size, modification date, ownership.
Pipe all output through `scripts/redact.sh` before storing evidence.
