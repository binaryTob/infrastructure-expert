---
id: "disk_analysis"
name: "Disk Analysis"
version: "1.0"
category: "disk"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
provides: ["fs_usage", "inodes", "large_dirs", "mounts"]
triggers: []
false_positives:
  - "Filesystem near full but with reserved blocks for root (ext default 5%): verify available for app user."
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/disk" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Disk Analysis

## Objective
Filesystem usage, inodes, largest directories, mount options, disk topology.

## Commands

### Filesystem usage
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== DF ==="; df -hT -x tmpfs -x devtmpfs 2>/dev/null; echo; echo "=== INODES ==="; df -i -x tmpfs -x devtmpfs 2>/dev/null; echo; echo "=== LSBLK ==="; lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT 2>/dev/null'
```

### Mount options
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'findmnt --real 2>/dev/null | head -60; echo; echo "=== MOUNT ==="; mount | grep -vE "tmpfs|proc|sysfs|cgroup|devpts|mqueue|shm|fusectl" | head -40'
```

### Largest directories (top 20)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'du -x --max-depth=3 / 2>/dev/null | sort -rn | head -20'
```

### Large files
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'find / -xdev -type f -size +100M -exec ls -lh {} \; 2>/dev/null | sort -k5 -hr | head -15'
```

### Disk monitoring (smartctl if available)
```bash
# [risk:ro] [mode:auto] [requires:smartctl]
ssh {{SSH_TARGET}} 'for d in $(lsblk -nd -o NAME 2>/dev/null); do smartctl -H /dev/$d 2>/dev/null; done || echo "smartctl no disponible"'
```

## Analysis
- df Use% > 85%: WARNING. > 95%: CRITICAL.
- Inode Use% > 85%: WARNING (even if space free, cannot create files).
- Noatime/nodiratime in mount options: good for performance.
- `/var/log` growing: cross-reference with `log_analysis`.
- Snap-based /loop mounts: identify which applications.

## Thresholds
| Metric | NORMAL | WATCH | WARNING | CRITICAL |
|--------|--------|-------|---------|----------|
| fs usage % | < 70 | 70-85 | 85-95 | > 95 |
| inodes % | < 70 | 70-85 | 85-95 | > 95 |

## Security
Read-only.
