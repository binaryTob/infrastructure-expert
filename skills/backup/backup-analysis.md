---
id: "backup_analysis"
name: "Backup Analysis"
version: "3.0"
category: "backup"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
triggers: []
provides: ["backup_mechanisms", "db_backups", "filesystem_backups", "restore_readiness", "etcd_snapshots"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/backup" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Backup Analysis

## Objective
Detect backup mechanisms and — critically — whether restore is likely to work, on ANY
host (VM, Docker, Kubernetes). Distinguish "a backup job exists" from "a restore was
ever tested". No backup for persistent data is a CRITICAL finding.

## Commands

### Cron / timer backup jobs (runs always)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== CRONTAB ==="; cat /etc/crontab 2>/dev/null; ls /etc/cron.d/ 2>/dev/null; echo "=== BACKUP ENTRIES ==="; grep -riE "backup|dump|snapshot|archive|rsync|borg|restic|duplicity|pg_dump|mysqldump|mongodump|tar " /etc/crontab /etc/cron.d/ /etc/cron.daily/ /etc/cron.weekly/ /var/spool/cron/crontabs/ 2>/dev/null | grep -vE "^\s*#" | head -40 || echo "no-backup-cron"'
```

### Systemd backup timers (runs always)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'systemctl list-timers --all 2>/dev/null | grep -iE "backup|dump|snapshot|borg|restic|certbot|renew" || echo "no-backup-timers"'
```

### Database backup scripts (runs always — local + remote DB)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'grep -rliE "pg_dump|mysqldump|mongodump|redis-cli.*save|sqlite3 .* .backup" /opt /usr/local/bin /home /root /etc 2>/dev/null | head -20 || echo "no-db-dump-scripts"; echo "=== REMOTE DB CONFIG ==="; grep -rhoiE "host:? [A-Za-z0-9.\-]+|hostname[:=] [A-Za-z0-9.\-]+|DB_HOST[=: ][A-Za-z0-9.\-]+" /opt /home /root /etc 2>/dev/null | grep -vE "localhost|127.0.0.1" | sort -u | head -20'
```

### Backup destination + off-site (runs always)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'grep -rhiE "rclone|s3://|s3cmd|gs://|azure|scp |rsync .*@|gdrive|dropbox|backblaze" /etc /opt /usr/local/bin /home /root 2>/dev/null | grep -vE "^\s*#" | head -20 || echo "no-offsite-destination-detected"'
```

### Backup freshness (recent backup artifacts)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'find / -maxdepth 4 -type f \( -name "*.dump" -o -name "*.sql.gz" -o -name "*.tar.gz" -o -name "*.bak" -o -name "*.snap" \) -mtime -14 2>/dev/null | grep -viE "/proc|/sys|/usr/lib|/var/lib/docker" | head -30 || echo "no-recent-backup-artifacts"'
```

### Kubernetes-native backups (if k8s present)
```bash
# [risk:ro] [mode:auto] [requires:kubectl]
ssh {{SSH_TARGET}} 'kubectl get pods -A 2>/dev/null | grep -iE "velero|restic|borg|backup" || echo "no-backup-operator"; echo ===; kubectl get crd 2>/dev/null | grep -iE "snapshot|backup|velero" || echo "no-backup-crd"; echo ===; ls /var/lib/etcd/member/snap 2>/dev/null || echo "no-etcd-snapdir"'
```

## Analysis

- **No backup mechanism + persistent data present** (DB, uploads, volumes): CRITICAL data-loss risk.
- **Backup job exists but destination is on the SAME disk/host**: not a real backup — one disk failure loses both.
- **No off-site/remote destination**: MEDIUM/HIGH — no protection against host-level failure.
- **Backup jobs exist but no evidence of a recent artifact (< 14 days)**: job likely failing silently — WARNING.
- **No restore test ever**: "backup exists" != "restore works". Flag as HIGH if data is critical.
- **Remote database (host != localhost)**: the DB may live elsewhere; verify whether its backups are this host's responsibility or the DB host's.
- **Certbot/renew timer absent while using Let's Encrypt**: cert expiry outage risk (cross-ref `tls_certificate_analysis`).

### Kubernetes hosts
- No velero/backup operator + `local-path` PVCs = no automated volume snapshots; CRITICAL.
- No etcd snapshot automation = etcd state unrecoverable on corruption.

## False Positives
- A `.tar.gz` in a source tree is NOT a backup artifact — check the path and mtime context before counting it.
- Cron jobs referencing "backup" in a comment only (`#`) are excluded; don't flag commented-out jobs.

## Evidence
- `cron-backups.txt`, `backup-timers.txt`, `db-dump-scripts.txt`, `offsite.txt`, `freshness.txt`, `k8s-backup.txt`

## Security
Read-only. Never run a restore. Report "restore readiness" as a recommendation for the operator to test.
