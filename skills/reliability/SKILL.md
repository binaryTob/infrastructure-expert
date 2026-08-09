---
name: reliability-analysis
area: reliability
description: Reliability review: control-plane HA, etcd, SPOFs, restart strategy, storage HA, multi-node distribution, ingress-layer resilience.
purpose: Identify single points of failure that could take the whole platform down or lose data.
safety: L1
applies_when: ["kubernetes cluster present"]
discovery:
  - "kubectl get pods -A -o wide | grep -E 'etcd|kube-apiserver|kube-scheduler|kube-controller-manager'"
  - "kubectl get nodes -o wide"
  - "kubectl get pvc -A; kubectl get storageclass"
  - "kubectl get deploy,sts -A -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name} replicas={.spec.replicas}{\"\n\"}{end}'"
  - "kubectl get pods -A | awk 'NR>1 && $5 !~ /^0/'  (restarts > 0)"
tests:
  - "count etcd pods (kubectl get pods -A | grep etcd) -> assert >=3 for HA; ETCDCTL_API=3 etcdctl member list if available"
evidence_artifacts: ["25_k8s_nodes.yml","26_k8s_pods.yml","43_netpol_pvc_sc.yml"]
interpretation: |
  etcd members <3 = NO HA. Loss of the single etcd node = total cluster state loss unless backed up.
  Single control-plane node + worker = if CP node dies, cluster API dies; workloads on the worker keep running but no control plane.
  CP node with no taint -> app pods co-scheduled with etcd/apiserver -> noisy neighbor + larger blast radius.
  local-path PVCs node-bound, RWO, Delete reclaim -> if node lost, data lost.
  Stateful workloads with only 1 replica on a single node = total data loss if that node dies.
  Ingress controller as DaemonSet on all nodes = good HA for ingress (survives node loss).
  CrashLoop pods failing for extended periods = no monitoring/alerting -> silent outage risk.
risk_model: |
  Single etcd / single control plane = CRITICAL for a production platform.
  Irreplaceable data on single local-path PVC with no evidenced backup = CRITICAL.
  CrashLoop + down monitoring = HIGH.
references: ["https://etcd.io/docs/v3.5/faq/"]
---

# Reliability Analysis

Count etcd members BEFORE claiming HA. One etcd pod = one Raft member = zero fault
tolerance. Always tie data-loss claims to BOTH the storage class (local-path =>
node-bound) AND the absence of a documented, tested backup (backup != restore).
