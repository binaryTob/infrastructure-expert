---
id: "log_analysis"
name: "Log Analysis"
version: "2.0"
category: "logging"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
provides: ["journal_errors", "oom_in_logs", "disk_errors", "log_disk_usage"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/logs" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Log Analysis

Detect errors, OOMs, disk errors, and log disk usage from journal and dmesg.

This skill OWNS the OOM-in-logs detection (memory_analysis no longer duplicates this).
It does NOT run `smartctl` — that is owned by `disk_analysis`.

## Commands

### Journal error count (last 24h)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'journalctl --since "24 hours ago" -p err --no-pager 2>/dev/null | head -40; echo; echo "=== DMESG ERRORS ==="; dmesg -T 2>/dev/null | grep -iE "error|fail|warn" | tail -20'
```

### OOM in logs (canonical source — memory_analysis does NOT duplicate this)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== JOURNAL OOM ==="; journalctl -k --no-pager 2>/dev/null | grep -iE "out of memory|oom-kill|killed process|memory pressure" | tail -20; echo; echo "=== DMESG OOM ==="; dmesg -T 2>/dev/null | grep -iE "out of memory|oom-kill|killed process" | tail -10'
```

### Disk errors (kernel logs only — smartctl is in disk_analysis)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'dmesg -T 2>/dev/null | grep -iE "I/O error|ata.*error|sd.*error|read error|write error|bad sector|filesystem.*error" | tail -15'
```

### Log disk usage
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== /var/log SIZE ==="; du -sh /var/log 2>/dev/null; echo; echo "=== JOURNAL SIZE ==="; du -sh /var/log/journal 2>/dev/null; echo; echo "=== LARGEST LOGS ==="; find /var/log -type f \( -name "*.log" -o -name "*.gz" \) 2>/dev/null | xargs ls -lhS 2>/dev/null | head -15'
```

### Authentication errors
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== SSH FAILED ==="; journalctl -u ssh --since "7 days ago" --no-pager 2>/dev/null | grep -i "failed\|invalid" | tail -20; echo; echo "=== SUDO FAILURES ==="; grep -i "authentication failure\|FAILED su" /var/log/auth.log 2>/dev/null | tail -15 || journalctl _COMM=sudo --no-pager 2>/dev/null | grep -i "failure" | tail -15'
```

## Analysis
- Frequent OOM kills: cross-reference with `memory_analysis` (live PSI/RSS/swap) and identify the victim process.
- Disk errors in dmesg: CRITICAL (failing hardware). Cross-reference with `disk_analysis` smartctl evidence.
- `/var/log` > 5GB: implement log rotation.
- Authentication failures from unknown IPs: possible brute force. Cross-reference with `security_analysis`.
- `journalctl` disk pressure: check `SystemMaxUse` in `/etc/systemd/journald.conf`.

## Evidence
- `journal-errors.txt`, `oom.txt`, `disk-errors.txt`, `log-usage.txt`, `auth.txt`

## Security
Read-only.