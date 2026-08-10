---
id: "observability_analysis"
name: "Observability Analysis"
version: "2.0"
category: "observability"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["kubernetes_analysis"]
triggers: []
provides: ["monitoring_stack", "metrics_available", "logging_stack", "alerting_status"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/observability" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Observability Analysis

Detect metrics, logs, traces, alerting, and dashboards. Determine if the platform can
detect its own failures.

This skill CONSUMES evidence from `kubernetes_analysis` (pods list, services list,
`kubectl top nodes`). It only runs additional commands for observability-specific
data not covered there.

## Commands (single fetch + local grep, not 9 separate kubectl calls)

### Monitoring stack detection (one command, all greps)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== MONITORING PODS ==="; kubectl get pods -A 2>/dev/null | grep -iE "prometheus|grafana|loki|otel|opentelemetry|jaeger|alertmanager|node.exporter|kube-state-metrics|metrics-server|cadvisor|fluent|vector|logstash|filebeat|elastic" || echo "no monitoring pods found"'
```

### Monitoring services
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== MONITORING SVC ==="; kubectl get svc -A 2>/dev/null | grep -iE "prometheus|grafana|loki|alertmanager" || echo "no monitoring svc found"'
```

### Metrics API availability
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== METRICS API ==="; kubectl get --raw /metrics 2>/dev/null | head -5 || echo "metrics API no disponible"'
```

### Host-level monitoring
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'systemctl list-units --type=service --state=running 2>/dev/null | grep -iE "collectd|telegraf|node_exporter|prometheus|grafana" || echo "no host monitoring"'
```

## Analysis
- Read `kubernetes/top.txt` from kubernetes_analysis for `kubectl top nodes` evidence.
- Prometheus in CrashLoopBackOff = metrics collection broken -> no HPA, no kubectl top, no alerting.
- Grafana present but Prometheus down = dashboards show stale/empty data.
- kube-state-metrics + node-exporter running but scraper down = they emit but nobody consumes.
- No metrics-server = no `kubectl top`, no HPA, no VPA.
- No Alertmanager + no Grafana alerts = alerting gap -> silent outages.
- Host-level monitoring (collectd/snmpd) running: verify exposure.

## Evidence
- `monitoring-pods.txt`, `monitoring-svc.txt`, `metrics-api.txt`, `host-monitoring.txt`

## Security
Read-only. A monitoring stack whose scraper is down is worse than no stack.