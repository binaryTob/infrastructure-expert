---
id: "http_health_analysis"
name: "HTTP Application Health Analysis"
version: "1.0"
category: "web"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "network_analysis"]
triggers: ["PRESENT:http_server", "PRESENT:apache2", "PRESENT:httpd", "PRESENT:nginx"]
provides: ["endpoint_status", "redirect_chains", "response_times", "upstream_health", "security_headers", "internal_vs_external_reachability"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/http" }
  SSH_TARGET: { type: "string", required: true }
  SLOW_MS: { type: "integer", default: 1500, description: "Umbral de respuesta lenta en ms" }
output: { format: "json", schema: "output_schema" }
---

# HTTP Application Health Analysis

## Objective
Probe the actual HTTP endpoints served by this host — status codes, redirect chains,
response latency, security headers — and compare internal (localhost) vs external
reachability. This detects the *symptoms* (5xx, slow, redirect loop) that the web-server
and log skills then turn into root causes.

## Commands

### Discover domains to probe (from vhosts + certs)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} '{ grep -rhoiE "ServerName [A-Za-z0-9.\-]+" /etc/apache2 /etc/httpd /etc/nginx 2>/dev/null | awk "{print \$2}"; ls -1 /etc/letsencrypt/live/ 2>/dev/null; } | sort -u'
```

### Status + latency for each discovered domain (internal probe)
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'for d in $( { grep -rhoiE "ServerName [A-Za-z0-9.\-]+" /etc/apache2 /etc/httpd /etc/nginx 2>/dev/null | awk "{print \$2}"; ls -1 /etc/letsencrypt/live/ 2>/dev/null; } | sort -u ); do [ -z "$d" ] && continue; res=$(curl -sk -o /dev/null -w "%{http_code} %{time_total}s" --connect-timeout 5 --max-time 12 -H "Host: $d" https://localhost/ 2>/dev/null); echo "$d -> $res"; done'
```

### Redirect chain (follow and list every hop)
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'for d in $(ls -1 /etc/letsencrypt/live/ 2>/dev/null); do echo "=== $d ==="; curl -sk -I -L --connect-timeout 5 --max-time 12 -H "Host: $d" https://localhost/ 2>/dev/null | grep -iE "^HTTP|^location:"; done'
```

### Root path + common health paths
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'for d in $(ls -1 /etc/letsencrypt/live/ 2>/dev/null); do for p in / /health /healthz /api/health /ping; do code=$(curl -sk -o /dev/null -w "%{http_code}" --connect-timeout 4 --max-time 8 -H "Host: $d" "https://localhost$p" 2>/dev/null); [ "$code" != "000" ] && echo "$d$p -> $code"; done; done'
```

### Security + cache headers on root
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'd=$(ls -1 /etc/letsencrypt/live/ 2>/dev/null | head -1); [ -n "$d" ] && curl -sk -I --connect-timeout 5 --max-time 10 -H "Host: $d" https://localhost/ 2>/dev/null | grep -iE "strict-transport|content-security|x-frame|x-content-type|referrer-policy|server:|cache-control"'
```

### Internal (localhost) vs external (public DNS) reachability
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'for d in $(ls -1 /etc/letsencrypt/live/ 2>/dev/null); do int=$(curl -sk -o /dev/null -w "%{http_code}" --connect-timeout 4 --max-time 8 -H "Host: $d" https://localhost/ 2>/dev/null); ext=$(curl -sk -o /dev/null -w "%{http_code}" --connect-timeout 6 --max-time 12 "https://$d/" 2>/dev/null); echo "$d internal=$int external=$ext"; done'
```

## Analysis

- **5xx** = application or upstream failure; hand to `web_server_analysis` (proxy map) + `log_analysis` (app logs). 502 = upstream down, 503 = overloaded, 504 = timeout.
- **000** = connection refused/timeout — nothing listening, or the backend crashed.
- **internal 200 but external 5xx/000** = problem is at the edge (firewall, NAT, WAF, cloud LB), NOT the app.
- **Redirect chain > 3 hops or a loop** = misconfigured redirects (http->https->http, missing trailing slash).
- **`time_total` > {{SLOW_MS}} ms** on the root path = slow app; correlate with `capacity_analysis` (CPU/mem) and `log_analysis`.
- **Missing security headers** (`strict-transport-security`, `x-content-type-options`) = hardening gap, MEDIUM.
- **`Server:` header leaking exact version** = minor info disclosure.

## False Positives
- `000` on `/health` when the app simply has no such route (404 is normal, 000 is not) — verify the route exists before flagging.
- Slow first request right after a cold start (JIT, asset precompile) is not a steady-state slowness finding.

## Evidence
- `domains.txt`, `status.txt`, `redirects.txt`, `health-paths.txt`, `headers.txt`, `reachability.txt`

## Security
Read-only. Only HEAD/GET probes to local endpoints and public DNS. No payloads, no fuzzing, no auth attempts.
