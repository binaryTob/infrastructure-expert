---
name: performance-analysis
area: performance
description: Host + cluster resource posture: CPU/RAM/disk/load, node capacity/allocatable, QoS distribution, resource requests/limits, throttling/OOM signals.
purpose: Detect under/over-provisioning, resource leaks, misconfigured limits, single points of contention.
safety: L1
applies_when: ["always"]
discovery:
  - "nproc; lscpu | head -20; free -h; cat /proc/loadavg"
  - "df -hT -x tmpfs -x devtmpfs; lsblk"
  - "kubectl describe node <node> | grep -E 'Capacity|Allocatable|Allocated|cpu |memory '"
  - "kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name} qos={.status.qosClass}{\"\n\"}{end}'"
  - "kubectl top nodes; kubectl top pods -A"
tests:
  - "kubectl get --raw /metrics 2>/dev/null | grep -E 'container_cpu|container_memory' (if metrics api present)"
evidence_artifacts: ["02_resources.yml","03_disks.yml","46_nodes_top.yml"]
interpretation: |
  node cpu requests <15% of capacity = under-committed (headroom fine; cost issue).
  BestEffort pods in production = no guarantee; first evicted under MemoryPressure.
  No requests at all = scheduler blind; can overpack a node until OOM.
  0 swap (k8s default) = OK. Single disk for etcd+docker = IOPS contention risk.
  Metrics API unavailable = cannot assess real utilization (see observability).
risk_model: |
  Missing resource requests/limits on prod workloads = MEDIUM reliability/performance.
  Single disk shared etcd+container = MEDIUM.
references: ["https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/"]
---

# Performance Analysis

Real utilization needs metrics API; if Prometheus/metrics-server is down, you can
only assert CAPACITY expectations from requests/limits, not actual usage. State
that distinction explicitly.