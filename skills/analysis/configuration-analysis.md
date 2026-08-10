---
id: "configuration_analysis"
name: "Configuration Analysis"
version: "2.0"
category: "configuration"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["systemd_analysis"]
provides: ["sysctl", "limits", "webserver_config", "db_config_summary"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/configuration" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Configuration Analysis

## Objective
Review key system configuration parameters: sysctl, ulimits, web server configs, and database configs.

## Commands

### sysctl (key network + kernel params)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'sysctl -a 2>/dev/null | grep -E "net\.(core\.somaxconn|ipv4\.tcp_fin_timeout|ipv4\.tcp_tw_reuse|ipv4\.tcp_max_syn_backlog|ipv4\.ip_local_port_range)|vm\.(swappiness|overcommit_memory|overcommit_ratio|dirty_ratio|dirty_background_ratio|max_map_count)|fs\.(file-max|inotify\.max_user_watches)" 2>/dev/null'
```

### Limits
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== /etc/security/limits.conf ==="; grep -v "^#" /etc/security/limits.conf 2>/dev/null | grep -v "^$" | head -20; echo; echo "=== /etc/security/limits.d/ ==="; cat /etc/security/limits.d/*.conf 2>/dev/null | head -40; echo; echo "=== SYSTEMD LIMITS ==="; systemctl show --property=DefaultLimitNOFILE,DefaultLimitNPROC 2>/dev/null'
```

### Nginx config (if present)
```bash
# [risk:ro] [mode:auto] [requires:nginx]
ssh {{SSH_TARGET}} 'nginx -T 2>/dev/null | grep -E "worker_connections|worker_processes|keepalive|gzip|error_log|access_log|listen|server_name|proxy_pass" | head -60 || echo "nginx -T no disponible"'
```

### Apache config (if present)
```bash
# [risk:ro] [mode:auto] [requires:apache2]
ssh {{SSH_TARGET}} 'apachectl -S 2>/dev/null || apache2ctl -S 2>/dev/null || httpd -S 2>/dev/null || echo "apache no disponible"'
```

### Ulimits per running process (top memory consumers)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for pid in $(ps -eo pid --sort=-rss --no-headers | head -10); do echo "PID $pid:"; cat /proc/$pid/limits 2>/dev/null | grep "Max open files"; done'
```

### Transparent Huge Pages
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null; echo; cat /sys/kernel/mm/transparent_hugepage/defrag 2>/dev/null'
```

## Analysis
- `net.ipv4.tcp_tw_reuse=1` with low `tcp_fin_timeout`: good for high-connection servers.
- `vm.swappiness=0` in K8s: good. `=60` (default): can cause unnecessary swapping.
- `fs.file-max` < 200k: low for production servers.
- `worker_connections` in Nginx: total = `worker_processes * worker_connections`.
- Transparent Huge Pages: `always` = problematic for Redis/MongoDB (latency spikes).
- `vm.overcommit_memory=2` with correct `overcommit_ratio`: strict OOM prevention (good for K8s).

## Evidence
- `sysctl.txt`, `limits.txt`, `nginx.txt`, `apache.txt`, `ulimits.txt`, `thp.txt`

## Security
Read-only.
