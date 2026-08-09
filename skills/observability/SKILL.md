---
name: observability-analysis
area: observability
description: Detect logs/metrics/traces/alerting/dashboards; assess what is monitored, what is broken, retention, alerting gaps.
purpose: Determine whether the platform can detect its own failures.
safety: L1
applies_when: ["always"]
discovery:
  - "kubectl get pods -A | grep -iE 'prometheus|grafana|loki|vector|fluent|jaeger|node-exporter|cadvisor|elastic|otel'"
  - "kubectl get svc -A | grep -iE 'prometheus|grafana|loki'"
  - "kubectl top nodes; kubectl top pods -A"
  - "systemctl list-units --type=service --state=running | grep -iE 'collectd|prometheus|grafana|node_exporter'"
  - "kubectl get pods -A -o wide | grep -iE 'prometheus'  (note crashloop)"
tests:
  - "kubectl get --raw /metrics  (metrics API present?)"
evidence_artifacts: ["09_services_running.yml","26_k8s_pods.yml","46_nodes_top.yml"]
interpretation: |
  Prometheus in CrashLoopBackOff (exit 2) = metrics collection broken -> no HPA, no
  alerting on metrics, no `kubectl top`. Grafana present (namespace grafana-dashboard)
  but depends on Prometheus -> dashboards show stale/empty data.
  kube-state-metrics + node-exporter running but their scraper (prometheus) is down
  -> they emit but nobody consumes. Alerting gap = silent outages.
  collectd + snmpd running at host level = some host monitoring (but insecure SNMP exposure to verify).
risk_model: |
  Monitoring scraper crashloop => alerting blind = HIGH (silent outages).
  SNMP exposed (snmpd) without verified restriction = MEDIUM.
remediation_template: ~
references: ["https://prometheus.io/docs/"]
---

# Observability Analysis

A monitoring stack whose SCRAPER is down is worse than no stack: dashboards lie
(stale data) while operators believe they have visibility. Always check the
collector pod status, not just that a stack exists.