---
id: "web_server_analysis"
name: "Web Server & Reverse Proxy Analysis"
version: "1.0"
category: "web"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "network_analysis"]
triggers: ["PRESENT:apache2", "PRESENT:httpd", "PRESENT:nginx", "PRESENT:haproxy", "PRESENT:http_server"]
provides: ["webserver_engine", "vhosts", "proxy_upstream_map", "proxy_status", "upstream_health"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/web" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Web Server & Reverse Proxy Analysis

## Objective
Detect the web server / reverse proxy engine (Apache, nginx, HAProxy), enumerate its
virtual hosts, map every `ProxyPass` / `proxy_pass` / `backend` to its upstream target,
and verify upstream health. This is the skill that turns a `502/503/504` into a root cause:
proxy config -> upstream target -> backend process -> reachability.

Runs only when a web server is detected (`triggers`). Not applicable to pure-K8s ingress
(that is `ingress_nginx_analysis` / `traefik_analysis`).

## Commands

### Engine + version
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for b in apache2 httpd nginx haproxy caddy; do command -v $b >/dev/null 2>&1 && echo "ENGINE:$b $($b -v 2>&1 | head -1)"; done; echo ===; ss -H -tlnp 2>/dev/null | grep -E ":80 |:443 |:8080 |:8443 " | head -20'
```

### Apache vhosts + proxy mapping (if apache/httpd present)
```bash
# [risk:ro] [mode:auto] [requires:apache2]
ssh {{SSH_TARGET}} 'echo "=== ENABLED SITES ==="; ls -1 /etc/apache2/sites-enabled/ 2>/dev/null || ls -1 /etc/httpd/conf.d/ 2>/dev/null; echo; echo "=== VHOSTS + PROXY ==="; grep -rniE "ServerName|ServerAlias|ProxyPass|ProxyPassReverse|BalancerMember|Listen " /etc/apache2/sites-enabled/ /etc/apache2/sites-available/ /etc/httpd/conf.d/ /etc/httpd/conf/ 2>/dev/null | grep -vE "^\s*#" | head -80'
```

### nginx vhosts + proxy mapping (if nginx present)
```bash
# [risk:ro] [mode:auto] [requires:nginx]
ssh {{SSH_TARGET}} 'echo "=== NGINX CONF ==="; nginx -T 2>/dev/null | grep -nE "server_name|proxy_pass|upstream|listen |location " | grep -vE "^\s*#" | head -80 || grep -rniE "server_name|proxy_pass|upstream|listen " /etc/nginx/ 2>/dev/null | grep -vE "^\s*#" | head -80'
```

### HAProxy backends (if haproxy present)
```bash
# [risk:ro] [mode:auto] [requires:haproxy]
ssh {{SSH_TARGET}} 'grep -rniE "frontend|backend|server |bind |mode " /etc/haproxy/haproxy.cfg 2>/dev/null | grep -vE "^\s*#" | head -60'
```

### Map proxy target -> live backend (the 502 diagnostic chain)
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'targets=$(grep -rhoiE "ProxyPass(Reverse)? /? http[s]?://[^ ]+|proxy_pass http[s]?://[^ ;]+" /etc/apache2 /etc/httpd /etc/nginx 2>/dev/null | sed -E "s#(ProxyPass(Reverse)?|proxy_pass)[^:]*:?##" "" | sort -u); for t in $targets; do host=$(echo "$t" | sed -E "s#https?://##"); code=$(curl -sk -o /dev/null -w "%{http_code}" --connect-timeout 3 --max-time 5 "http://$host/" 2>/dev/null); echo "UPSTREAM $t -> HTTP $code"; done'
```

### Error log tail (last 40 lines across web server logs)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ls -1 /var/log/apache2/ 2>/dev/null; tail -n 40 /var/log/apache2/error.log 2>/dev/null; tail -n 40 /var/log/nginx/error.log 2>/dev/null; tail -n 40 /var/log/httpd/error_log 2>/dev/null'
```

## Analysis

- **502 Bad Gateway** = proxy reached, upstream did NOT answer correctly. Classic causes:
  1. Upstream process dead/not listening (container up, app down — check the mapped port with `curl`).
  2. Upstream bound to wrong interface/port (config drift between proxy and app).
  3. Upstream crashed on request (segfault/OOM) — check dmesg/OOM + app logs.
- **503 Service Unavailable** = no healthy backend / all workers busy / `max_children` exhausted.
- **504 Gateway Timeout** = upstream accepted but did not respond in time (slow DB, hung backend).
- **421 Misdirected Request** on localhost:443 = SNI mismatch — vhost is SNI-scoped, use `-H "Host: domain"` or the real name to test locally.
- Map each `ProxyPass / http://localhost:PORT/` to the process on that port (`ss -tlnp`). If the port is a `docker-proxy`, follow it to the container IP and verify the app inside is listening (`curl <container-ip>:port`).
- An upstream that returns 200 directly but 502 through the proxy = proxy config points at the wrong target.
- No reverse proxy at all but 5xx = app-level error; go to `log_analysis` / `http_health_analysis`.

## Thresholds

| Metric | NORMAL | WATCH | WARNING | CRITICAL |
|--------|--------|-------|---------|----------|
| Upstream probes returning 5xx | 0 | 0 | 1 | >=1 |
| Error log growth (per hour) | low | moderate | high | flooding |

## False Positives
- A `ProxyPass` target being down during a rolling deploy is expected; correlate with `docker_analysis` restart counts before flagging.
- `421` on a localhost probe is NOT a server fault — it is SNI behavior; re-test with the correct `Host` header.

## Evidence
- `engine.txt`, `vhosts.txt`, `proxy-map.txt`, `upstream-probe.txt`, `error-log.txt`

## Security
Read-only. Never `service reload`/`restart`, never edit vhosts. A 5xx is diagnosed, not fixed, here.
