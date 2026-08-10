---
id: "reliability_analysis"
name: "Reliability Analysis"
version: "2.0"
category: "reliability"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["kubernetes_analysis"]
triggers: ["PRESENT:kubectl"]
provides: ["ha_status", "spof_list", "storage_ha", "restart_analysis"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/reliability" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Reliability Analysis

Identify single points of failure that could take the platform down or lose data.
This skill CONSUMES evidence from `kubernetes_analysis` (nodes, pods, PVC, storageclass
already fetched there). It only runs additional commands for data that kubernetes_analysis
does not cover: etcd member count, node taints, pod anti-affinity.

## Commands (only what kubernetes_analysis does NOT already fetch)

### Control plane pod count (single grep, not 4 separate kubectl calls)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get pods -A 2>/dev/null | grep -cE "etcd|kube-apiserver|kube-scheduler|kube-controller-manager"; echo ===; kubectl get pods -A 2>/dev/null | grep -E "etcd|kube-apiserver|kube-scheduler|kube-controller-manager" | awk "{print \$1, \$2}"'
```

### Node taints and roles (kubernetes_analysis fetches nodes -o wide but not taints)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get nodes -o custom-columns=NAME:.metadata.name,ROLES:.metadata.labels.node-role\.kubernetes\.io/control-plane,TAINTS:.spec.taints 2>/dev/null'
```

### Pod anti-affinity (not covered by kubernetes_analysis)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get pods -A -o jsonpath='"'"'{range .items[*]}{.metadata.namespace}/{.metadata.name} node={.spec.nodeName} affinity={.spec.affinity}{"\\n"}{end}'"'"' 2>/dev/null | grep -v "affinity=$" | head -30'
```

## Analysis (consume kubernetes_analysis evidence)
- Read `kubernetes/pods.txt` and `kubernetes/nodes.txt` for existing evidence.
- Count etcd members: <3 = NO HA. Loss of single etcd node = total cluster state loss.
- Single control-plane node: if it dies, API dies; workloads continue but no control plane.
- CP node with no taint: app pods co-scheduled with etcd -> noisy neighbor + larger blast radius.
- Read `kubernetes/storage.txt` for PVC/StorageClass evidence.
  - `local-path` PVCs node-bound, RWO, Delete reclaim: if node lost, data lost.
  - Stateful workloads with replica=1 on single node: total data loss if node dies.
- Ingress controller as DaemonSet on all nodes: good HA (survives node loss).
- Read `kubernetes/restarts.txt` for CrashLoop evidence.
  - CrashLoop for extended periods + no alerting: silent outage risk.

## Evidence
- `control-plane.txt`, `node-taints.txt`, `anti-affinity.txt`

## Security
Read-only.