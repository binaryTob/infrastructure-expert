---
name: kubernetes-analysis
area: kubernetes
description: Deep read-only analysis of a kubeadm/self-hosted Kubernetes cluster (nodes, workloads, ingress, TLS, RBAC, storage, reliability).
purpose: Produce facts about cluster topology, control-plane HA, workload health, ingress/TLS, RBAC, storage and resource management; identify SPOFs and crashloops.
safety: L1
prerequisites:
  - "kubectl context exists and can reach apiserver"
applies_when:
  - "command -v kubectl"
  - "kubectl get nodes exits 0"
inputs: []
discovery:
  - "kubectl get nodes -o wide"
  - "kubectl get pods -A -o wide"
  - "kubectl get svc -A"
  - "kubectl get deploy,daemonset,statefulset -A"
  - "kubectl get ingress -A"
  - "kubectl get ingressroute -A"
  - "kubectl get middleware -A"
  - "kubectl get helmreleases -A; helm list -A"
  - "kubectl get crd"
  - "kubectl get clusterissuer,issuer,certificate -A"
  - "kubectl get networkpolicy -A"
  - "kubectl get pvc -A; kubectl get storageclass; kubectl get pv"
tests:
  - "kubectl get --raw /healthz"
  - "kubectl describe node <cp-node> | grep -E 'Roles|Taints|Conditions|Capacity|Allocatable|Allocated'"
  - "kubectl top nodes; kubectl top pods -A --sort-by=cpu"
  - "ETCDCTL_API=3 etcdctl ... endpoint health; ... member list  (or count etcd pods)"
evidence_artifacts:
  - "25_k8s_nodes.yml"
  - "26_k8s_pods.yml"
  - "27_k8s_svc.yml"
  - "28_k8s_ingress.yml"
  - "29_k8s_workloads.yml"
  - "30_helm.yml"
  - "42_crds.yml"
  - "43_netpol_pvc_sc.yml"
  - "46_nodes_top.yml"
  - "49_etcd_rbac.yml"
interpretation: |
  - Count control-plane nodes: etcd/api/scheduler/controller pods. <3 etcd members = no HA.
  - Node Roles `<none>` on a node running apiserver = role label missing (cosmetic) but control-plane identifiable by pods.
  - Node with no taints + control plane → workloads co-scheduled with etcd → contention/noise.
  - CrashLoopBackOff/ContainerStatusUnknown pods with high RESTARTS = real defects. Get Exit Code (1=app,2=cfg,137=OOM,255=signal).
  - BestEffort QoS (no requests/limits) = no scheduling guarantee, first evicted under pressure.
  - Metrics API unavailable = metrics-server/Prometheus down → no HPA, no `kubectl top`, no alerting data.
  - local-path storageclass = node-bound, no HA, Delete reclaim → stateful data at risk if node lost.
  - No NetworkPolicy = full east-west pod reachability (zero segmentation).
  - RBAC: only system cluster-admin bindings = good default; extra Group/SA = review.
risk_model: |
  SPOF (etcd<3 / single control plane) = HIGH reliability.
  Crashloop + no monitoring = HIGH (silent outages).
  local-path for irreplaceable data (secrets mgr) = HIGH.
  BestEffort production pods = MEDIUM.
remediation_template: |
  WHAT/WHY/HOW/RISK/PRIORITY/VALIDATION/ROLLBACK  (see lib/severity.md)
references:
  - "https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/"
  - "https://kubernetes.io/docs/concepts/security/pod-security-standards/"
---

# Kubernetes Analysis

Run `discovery` then `tests`. For every CrashLoop pod, capture `kubectl describe`
(State/Reason/Exit Code/Last State) to classify. Cross-reference IngressRoute
service names against `kubectl get svc -A` to detect stale/renamed backend
references (Traefik returns 503 for missing services). Count etcd pods to assert
HA. Never `kubectl apply/delete`; read-only.