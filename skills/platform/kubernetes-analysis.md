---
id: "kubernetes_analysis"
name: "Kubernetes Analysis"
version: "1.1"
category: "kubernetes"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
triggers: ["PRESENT:kubectl"]
provides: ["nodes", "node_runtime_health", "pods", "resource_requests_limits", "pod_restarts", "storage_classes", "rbac"]
false_positives:
  - "No kubectl access does NOT mean no cluster; if k3s/rke2/microk8s processes exist, probe manually."
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/kubernetes" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Kubernetes Analysis

Deep read-only cluster analysis: nodes, workloads, services, ingress, TLS, RBAC, storage, reliability.

## Commands

### Nodes
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== NODES ==="; kubectl get nodes -o wide 2>/dev/null; echo; echo "=== NODE DETAIL ==="; kubectl describe nodes 2>/dev/null | grep -E "Name:|Roles:|Taints:|Conditions:|Capacity:|Allocatable:|Allocated resources:" | head -80'
```

### Namespaces
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get ns 2>/dev/null'
```

### Pods (all namespaces)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get pods -A -o wide 2>/dev/null | head -100'
```

### Restart counts
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get pods -A 2>/dev/null | awk '"'"'NR>1 && $5 !~ /^0/ {print}'"'"' | head -30'
```

### Workloads
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get deploy,daemonset,statefulset -A 2>/dev/null'
```

### Services
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get svc -A 2>/dev/null'
```

### Ingress
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== INGRESS ==="; kubectl get ingress -A 2>/dev/null; echo; echo "=== INGRESSROUTE ==="; kubectl get ingressroute -A 2>/dev/null; echo; echo "=== MIDDLEWARE ==="; kubectl get middleware -A 2>/dev/null'
```

### Helm releases
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== HELMRELEASES ==="; kubectl get helmreleases -A 2>/dev/null; echo; echo "=== HELM LIST ==="; helm list -A 2>/dev/null'
```

### CRDs
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get crd 2>/dev/null'
```

### TLS certificates
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get clusterissuer,issuer,certificate -A 2>/dev/null'
```

### NetworkPolicy
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get networkpolicy -A 2>/dev/null'
```

### Storage
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== PVC ==="; kubectl get pvc -A 2>/dev/null; echo; echo "=== SC ==="; kubectl get storageclass 2>/dev/null; echo; echo "=== PV ==="; kubectl get pv 2>/dev/null'
```

### RBAC
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== CLUSTERROLEBINDINGS ==="; kubectl get clusterrolebinding 2>/dev/null | head -30; echo; echo "=== SERVICEACCOUNTS ==="; kubectl get sa -A 2>/dev/null | head -30'
```

### Top nodes / pods
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== NODES TOP ==="; kubectl top nodes 2>/dev/null || echo "metrics server no disponible"; echo; echo "=== PODS TOP ==="; kubectl top pods -A --sort-by=cpu 2>/dev/null | head -30 || echo "metrics server no disponible"'
```

### Resource requests/limits
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get pods -A -o jsonpath='"'"'{range .items[*]}{.metadata.namespace}/{.metadata.name} qos={.status.qosClass}{"\\n"}{end}'"'"' 2>/dev/null | head -60'
```

### Health
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get --raw /healthz 2>/dev/null || echo "healthz no disponible"'
```

### Node lease vs runtime health
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== NODE CONDITIONS ==="; kubectl get nodes -o custom-columns=NAME:.metadata.name,READY:.status.conditions[-1].status,HEARTBEAT:.status.conditions[-1].lastHeartbeatTime 2>/dev/null; echo "=== NODE LEASES ==="; kubectl get lease -n kube-node-lease -o custom-columns=NAME:.metadata.name,RENEW:.spec.renewTime 2>/dev/null; echo "=== RUNTIME FAILURES ==="; kubectl get events -A --field-selector involvedObject.kind=Node 2>/dev/null | grep -E "ContainerGCFailed|ImageGCFailed|FailedCreatePodSandBox|NetworkNotReady|DeadlineExceeded" | tail -60'
```

### Non-healthy pods grouped by node
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get pods -A -o wide 2>/dev/null | grep -E "Terminating|CrashLoopBackOff|ContainerCreating|ContainerStatusUnknown|ContainerCannotRun|ImagePullBackOff|Error" | head -120'
```

## Analysis
- Count control-plane nodes: etcd/api/scheduler/controller pods. <3 etcd members = no HA.
- CrashLoopBackOff with high RESTARTS = real defects. Get Exit Code.
- BestEffort QoS = no requests/limits = no scheduling guarantee.
- Metrics API unavailable = no HPA, no `kubectl top`, no alerting.
- `local-path` storageclass = node-bound, no HA.
- No NetworkPolicy = full east-west pod reachability.
- RBAC: system cluster-admin bindings only = good default.
- A fresh node Lease only proves the kubelet can reach the API. Repeated runtime RPC
  timeouts plus stuck pods confirm a degraded node even when Kubernetes reports it `Ready`.
- Correlate runtime failures with local-path PVCs and StatefulSets: a replacement node
  cannot recover node-bound data without an explicit storage recovery procedure.

## Evidence
- `nodes.txt`, `node-runtime.txt`, `node-unhealthy-pods.txt`, `ns.txt`, `pods.txt`, `restarts.txt`, `workloads.txt`, `svc.txt`, `ingress.txt`, `helm.txt`, `crds.txt`, `tls.txt`, `netpol.txt`, `storage.txt`, `rbac.txt`, `top.txt`, `qos.txt`, `health.txt`

## Security
Read-only. Never `kubectl apply/delete`.
