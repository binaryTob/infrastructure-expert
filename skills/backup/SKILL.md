---
name: backup-analysis
area: backup
description: Detect backup mechanisms: cron jobs, velero, etcd snapshots, database dump scripts, PVC backup, restore procedures.
purpose: Distinguish "backup exists" from "restore works" — verify backup jobs are configured AND recently succeeded.
safety: L1
applies_when: ["always"]
discovery:
  - "ls -la /etc/cron* 2>/dev/null; cat /etc/crontab /etc/cron.d/* /var/spool/cron/crontabs/* 2>/dev/null"
  - "kubectl get pods -A | grep -iE 'velero|snapshot|backup|duplicati|restic|borg|borgmatic'"
  - "kubectl get pvc -A; kubectl get volumesnapshot -A 2>/dev/null; kubectl get snapshotschedule -A 2>/dev/null"
  - "ls /var/lib/etcd/member/snap 2>/dev/null; ls /etc/kubernetes/pki/etcd 2>/dev/null"
  - "kubectl describe etcdcluster -A 2>/dev/null"
tests:
  - "kubectl get --raw /healthz 2>/dev/null"
evidence_artifacts: ["13_cron.yml","43_netpol_pvc_sc.yml"]
interpretation: |
  No velero/backup operator pods -> no K8s-native backup (zero snapshots).
  No etcd snapshot cron job visible in cron -> etcd backup not evidenced.
  local-path PVCs with Delete reclaim -> no automated volume snapshot.
  Stateful workloads (databases, message brokers, password managers) on local-path
  without backups are at risk of total data loss if the node fails.
  Quorum replicas (e.g. multi-node message broker) provide resilience but NOT backup —
  they do not protect against logical corruption or operator error.
  FACT: If no backup mechanism detected for any persistent data and no etcd snapshot
  automation exists, flag as critical gap.
risk_model: |
  Zero backup coverage for stateful workloads + etcd = CRITICAL.
  local-path Delete reclaim + no snapshots = CRITICAL.
references: ["https://velero.io/"]
---

# Backup Analysis

"Backup exists" DOES NOT mean "restore works". Distinguish both. A PVC exists DOES
NOT mean "data is backed up." Quorum replicas are resilience NOT
backup — they don't protect against logical corruption or operator error. Mark
REQUIREMENT if no backup is found: "etcd snapshot cron job absent."
