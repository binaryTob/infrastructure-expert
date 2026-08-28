---
id: "web_secret_exposure"
name: "Web Server Secret Exposure Analysis"
version: "1.0"
category: "security"
phase: "forensic"
risk: "probe"
execution_mode: "auto"
depends_on: ["system_inventory", "network_analysis"]
triggers: ["PRESENT:http_server"]
provides: ["web_env_access", "web_config_exposure", "phpinfo_exposed"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/web-secret-exposure" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Web Server Secret Exposure Analysis

## Objective
Verify whether any web server on the host serves .env files, configuration files
with secrets, or exposes sensitive information through PHP info() or misconfigured
server directives.

## Commands

### 1. HTTP probe for .env files
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== PROBING .ENV VIA HTTP ==="; for port in 80 443 8080 8443 3000 8000 5000 8888 9000; do
  for path in "/.env" "/.env.local" "/.env.production" "/.env.backup" "/.env.development" "/.env.staging" "/env" "/config/env" "/assets/.env"; do
    code=$(curl -sk -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port$path" --max-time 3 2>/dev/null)
    [ "$code" != "404" ] && [ "$code" != "000" ] && [ "$code" != "403" ] && echo "[CRITICAL] port=$port path=$path HTTP_CODE=$code"
    [ "$code" = "403" ] && echo "[INFO] port=$port path=$path HTTP_CODE=403 (exists but forbidden)"
  done
done'
```

### 2. HTTP probe for config files
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== PROBING CONFIG FILES VIA HTTP ==="; for port in 80 443 8080 8443 3000 8000 5000; do
  for path in "/config.php" "/wp-config.php" "/wp-config.php.bak" "/database.yml" "/config.yml" "/settings.py" "/application.yml" "/.config/"; do
    code=$(curl -sk -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port$path" --max-time 3 2>/dev/null)
    [ "$code" != "404" ] && [ "$code" != "000" ] && [ "$code" != "403" ] && echo "[HIGH] port=$port path=$path HTTP_CODE=$code"
  done
done'
```

### 3. PHP info() exposure
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== PHP INFO EXPOSURE ==="; for port in 80 443 8080 8443 3000 8000; do
  result=$(curl -sk "http://127.0.0.1:$port/phpinfo.php" --max-time 3 2>/dev/null)
  echo "$result" | grep -qi "phpinfo()" && echo "[HIGH] PHP info() exposed on port $port"
  echo "$result" | grep -qi "PHP Version" && echo "[MEDIUM] PHP info page on port $port (may not be phpinfo.php)"
done'
```

### 4. nginx configuration analysis
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== NGINX CONFIG ==="; nginx -T 2>/dev/null | grep -nE "server_name|root |alias |location|\.env|try_files|proxy_pass" | head -40; echo; echo "=== NGINX SECURITY HEADERS ==="; nginx -T 2>/dev/null | grep -iE "X-Frame|X-Content|Strict-Transport|Content-Security|X-XSS" | head -10'
```

### 5. Apache configuration analysis
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== APACHE CONFIG ==="; grep -rnE "ServerName|DocumentRoot|Alias|Directory|Location|ProxyPass" /etc/apache2/sites-enabled/ 2>/dev/null | head -30; echo; echo "=== .HTACCESS ==="; find /var/www /srv -name ".htaccess" 2>/dev/null | while read f; do echo "FILE: $f"; grep -iE "env|secret|deny|redirect" "$f" 2>/dev/null; done'
```

### 6. Server response headers (information disclosure)
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET }} 'echo "=== RESPONSE HEADERS ==="; for port in 80 443 8080 8443; do
  echo "--- port $port ---"
  curl -skI "http://127.0.0.1:$port/" --max-time 3 2>/dev/null | head -15
done'
```

### 7. Backup files accessible via HTTP
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== BACKUP FILES VIA HTTP ==="; for port in 80 443 8080; do
  for path in "/backup.zip" "/backup.tar.gz" "/backup.sql" "/db.sql" "/database.sql" "/dump.sql" "/.git/HEAD" "/.svn/entries" "/.hg/dirstate"; do
    code=$(curl -sk -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port$path" --max-time 3 2>/dev/null)
    [ "$code" != "404" ] && [ "$code" != "000" ] && [ "$code" != "403" ] && echo "[HIGH] port=$port path=$path HTTP_CODE=$code"
  done
done'
```

### 8. Debug/admin endpoints exposed
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== DEBUG/ADMIN ENDPOINTS ==="; for port in 80 443 8080 3000 8000; do
  for path in "/debug" "/admin" "/phpmyadmin" "/adminer" "/server-status" "/server-info" "/.well-known/security.txt"; do
    code=$(curl -sk -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port$path" --max-time 3 2>/dev/null)
    [ "$code" != "404" ] && [ "$code" != "000" ] && [ "$code" != "403" ] && echo "[MEDIUM] port=$port path=$path HTTP_CODE=$code"
  done
done'
```

## Analysis

### Severity mapping
| Finding | Severity | Confidence |
|---------|----------|------------|
| HTTP 200 to /.env | CRITICAL | HIGH |
| HTTP 200 to wp-config.php.bak | CRITICAL | HIGH |
| PHP info() exposed | HIGH | HIGH |
| HTTP 200 to .git/HEAD | HIGH | HIGH |
| HTTP 200 to database config files | HIGH | HIGH |
| HTTP 403 to .env (file exists) | MEDIUM | HIGH |
| Missing security headers | LOW | HIGH |
| Debug endpoints exposed | MEDIUM | HIGH |
| Server version disclosed in headers | LOW | HIGH |
| Backup files accessible via HTTP | HIGH | HIGH |

### Correlation
- Cross-reference with `credential_exposure_analysis` for .env files in web dirs
- Cross-reference with `configuration_analysis` for server config details
- Cross-reference with `firewall_analysis` for external vs internal exposure

## Evidence
- `web-env-probe.yml` — HTTP probe results for .env files
- `web-config-probe.yml` — HTTP probe for config files
- `phpinfo-check.yml` — PHP info exposure results
- `nginx-config-analysis.yml` — nginx configuration analysis
- `apache-config-analysis.yml` — Apache configuration analysis
- `backup-files-exposed.yml` — backup files accessible via HTTP

## False Positives
- HTTP 403 to .env = file exists but is blocked (still a finding — file shouldn't be there)
- HTTP 200 to phpinfo.php in development/staging (expected, but flag for production)
- .git/HEAD accessible but repo is empty (check content)
- Backup files in non-production environments

## Security
This skill makes HTTP probes (L2 TEST level). It only reads HTTP status codes and
headers — it does not download or process any sensitive content. All evidence is
stored with redaction applied.
