---
id: "backup_analysis"
name: "Backup Analysis"
version: "2.0"
category: "backup"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["kubernetes_analysis"]
triggers: []
provides: ["backup_mechanisms", "etcd_snapshots", "pvc_backup", "restore_readiness"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/backup" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Backup Analysis

Detect backup mechanisms: velero, etcd snapshots, database dump scripts, PVC backup.
Distinguish "backup exists" from "restore works".

This skill CONSUMES evidence from `system_inventory` (cron jobs already detected there
via the runtime detection + config locations) and `kubernetes_analysis` (PVC/StorageClass
already fetched). It only runs commands for backup-specific detection.

## Commands (only backup-specific — cron and PVC evidence come from dependencies)

### Backup operators (velero etc)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get pods -A 2>/dev/null | grep -iE "velero|snapshot|backup|duplicati|restic|borg|borgmatic" || echo "no backup operator pods found"'
```

### VolumeSnapshot CRDs
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get volumesnapshot -A 2>/dev/null; echo ===; kubectl get snapshotschedule -A 2>/dev/null; echo ===; kubectl get crd 2>/dev/null | grep -iE "snapshot|backup|velero"'
```

### etcd snapshot presence
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== ETCD SNAP DIR ==="; ls /var/lib/etcd/member/snap 2>/dev/null || echo "no etcd snap dir"; echo "=== ETCD BACKUP CRON ==="; grep -r "etcdctl snapshot save" /etc/cron* /var/spool/cron/ 2>/dev/null || echo "no etcd backup cron found"'
```

### Database dump scripts
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'grep -r "pg_dump\|mysqldump\|redis-cli.*save\|mongodump" /etc/cron* /var/spool/cron/ /opt/ /usr/local/bin/ 2>/dev/null | head -20 || echo "no db dump scripts found"'
```

### Cron backup detection
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'cat /etc/crontab /etc/cron.d/* /var/spool/cron/crontabs/* 2>/dev/null | grep -iE "backup|dump|snapshot|archive|rsync|borg|restic" | grep -v "^#" || echo "no backup cron entries found"'
```

## Analysis (consume kubernetes_analysis evidence)
- Read `kubernetes/storage.txt` for PVC/StorageClass evidence.
  - `local-path` PVCs with Delete reclaim = no automated volume snapshot.
  - Stateful workloads on local-path without backups: CRITICAL data loss risk.
- No velero/backup operator pods = no K8s-native backup (zero snapshots).
- No etcd snapshot cron job = etcd backup not evidenced.
- Quorum replicas provide resilience but NOT backup: no protection against logical corruption.
- FACT: If no backup mechanism detected for persistent data and no etcd snapshot
  automation, flag as CRITICAL gap.

## Evidence
- `backup-operators.txt`, `volume-snapshots.txt`, `etcd-snapshots.txt`, `db-dump-scripts.txt`, `cron-backups.txt`

## Security
Read-only.