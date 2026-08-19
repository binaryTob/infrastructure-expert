---
id: "observability_analysis"
name: "Observability Analysis"
version: "3.0"
category: "observability"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "systemd_analysis"]
triggers: []
provides: ["monitoring_stack", "metrics_available", "logging_stack", "alerting_status", "log_rotation"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/observability" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Observability Analysis

## Objective
Determine whether the platform can detect its own failures: metrics, logs, alerting,
dashboards — on ANY host (VM, Docker, Kubernetes). A platform with no alerting fails
silently; that is itself a finding.

## Commands

### Host monitoring agents (runs always)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'systemctl list-units --type=service --state=running --no-legend 2>/dev/null | grep -iE "node_exporter|collectd|telegraf|prometheus|grafana|glances|zabbix|nrpe|nagios|icinga|datadog|newrelic|netdata" || echo "no-host-monitoring"; echo "=== EXPORTER PORTS ==="; ss -H -tlnp 2>/dev/null | grep -E ":9100 |:9090 |:3000 |:19999 " | head'
```

### Process managers (app-level supervision)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for b in pm2 supervisor systemd; do command -v $b >/dev/null 2>&1 && echo "SUPERVISOR:$b"; done; pm2 ls 2>/dev/null | head -20 || true'
```

### Log rotation (runs always)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== LOGRotate CONFIG ==="; ls /etc/logrotate.d/ 2>/dev/null; echo; echo "=== LARGE LOGS (no rotation risk) ==="; find /var/log /opt /home /root -type f -name "*.log" -size +500M 2>/dev/null | head -20 || echo "no-oversized-logs"'
```

### Docker log drivers (if docker present)
```bash
# [risk:ro] [mode:auto] [requires:docker]
ssh {{SSH_TARGET}} 'docker info --format "{{.LoggingDriver}}" 2>/dev/null; echo "=== CONTAINER LOG DRIVERS ==="; for c in $(docker ps -q 2>/dev/null | head -30); do name=$(docker inspect --format "{{.Name}}" $c | cut -c2-); ldrv=$(docker inspect --format "{{.HostConfig.LogConfig.Type}}" $c); echo "$name -> $ldrv"; done | sort'
```

### Alerting signals (runs always)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== ALERT CRONS ==="; grep -riE "alert|notify|mail -s|sendmail|ntfy|slack|telegram|pagerduty|webhook" /etc/crontab /etc/cron.d/ /var/spool/cron/crontabs/ /opt /usr/local/bin 2>/dev/null | grep -vE "^\s*#" | head -15 || echo "no-alerting-detected"; echo "=== EMAIL ==="; command -v sendmail postfix exim >/dev/null 2>&1 && echo "MTA-present" || echo "no-MTA"'
```

### Kubernetes monitoring (if k8s present)
```bash
# [risk:ro] [mode:auto] [requires:kubectl]
ssh {{SSH_TARGET}} 'kubectl get pods -A 2>/dev/null | grep -iE "prometheus|grafana|loki|alertmanager|node.exporter|kube-state-metrics|metrics-server|opentelemetry|jaeger" || echo "no-k8s-monitoring"; echo "=== METRICS API ==="; kubectl get --raw /metrics 2>/dev/null | head -3 || echo "metrics-api-unavailable"'
```

## Analysis

- **No monitoring + no alerting**: the platform cannot detect its own failure — a backend can 502 for days before anyone notices (exactly the silent-outage pattern). Severity scales with criticality of the traffic.
- **No log rotation + a log already > 500 MB**: disk-fill risk (a full disk takes down DBs, queues, and logins). This is often the *trigger* of a crash.
- **Docker `json-file` log driver without `max-size`**: container logs grow unbounded and fill the host disk.
- **`no-MTA` + no webhook alerting**: no way for cron failures to reach a human.
- **Monitoring present but no alert rules/dashboards**: metrics are emitted but nobody looks; still blind.

### Kubernetes hosts
- Prometheus CrashLoop = no metrics collection, no HPA, no alerting.
- No metrics-server = no `kubectl top`, no HPA.
- No Alertmanager + no Grafana alerts = silent outages.

## False Positives
- Absence of `node_exporter`/`prometheus` on a host that is monitored externally by a SaaS agent not visible locally — check for cloud/SaaS agent binaries before flagging "no monitoring".
- `json-file` log driver is fine when `max-size`/`max-file` are set; check `daemon.json` before flagging.

## Evidence
- `host-monitoring.txt`, `supervisors.txt`, `logrotate.txt`, `docker-logdrv.txt`, `alerting.txt`, `k8s-monitoring.txt`

## Security
Read-only. Never change log drivers, logrotate config, or restart monitoring agents (Level 3).
