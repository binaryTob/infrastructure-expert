---
id: "process_analysis"
name: "Process Analysis"
version: "2.0"
category: "process"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
provides: ["top_cpu_processes", "top_mem_processes", "zombies", "orphans", "root_processes"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/processes" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Process Analysis

Rank processes by CPU/RAM, detect zombies, orphans, and suspicious processes.

This skill OWNS all `ps` commands. The port->process map belongs to `network_analysis`
(removed from here to avoid duplication with `ss -tlnp` already run there).
security_analysis greps the `all-processes.txt` evidence from this skill rather than
re-running `ps aux`.

## Commands

### All processes (one fetch — security_analysis greps this cached evidence)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ps aux --sort=-%cpu | head -40'
```

### Full process tree
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ps axfo pid,ppid,user,pcpu,pmem,stat,comm,args --sort=-pcpu | head -50'
```

### Zombies / orphans
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== ZOMBIES ==="; ps -eo pid,ppid,stat,comm --no-headers | awk '"'"'$3 ~ /Z/ {print}'"'"'; echo; echo "=== ORPHANS (PPID=1, no systemd) ==="; ps -eo pid,ppid,user,comm --no-headers | awk '"'"'$2==1 && $4 !~ /^(systemd|init)$/ {print}'"'"' | head -20'
```

### Processes by user
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ps -eo user --no-headers | sort | uniq -c | sort -rn'
```

### Processes listening on 0.0.0.0 (filtered from ps — port map itself lives in network_analysis)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ps -eo pid,user,comm --no-headers | sort'
```

### Kernel threads
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ps -eo pid,ppid,comm --no-headers | awk '"'"'$3 ~ /^\[/ {print}'"'"' | head -20'
```

## Analysis
- Zombies > 0: processes that have already finished but the parent hasn't read their exit status.
- Root processes listening on 0.0.0.0 without known service: investigate.
- Orphans (PPID=1) not in systemd: process launched manually or from a daemon.
- High RSS with low CPU: resident memory, not necessarily active.
- Process changed name: `comm` vs `args` mismatch.
- security_analysis will grep `all-processes.txt` for `xmrig|kdevtmpfsi|kinsing|backdoor|reverse`.

## Evidence
- `all-processes.txt`, `tree.txt`, `zombies.txt`, `users.txt`, `kthreads.txt`

## Security
Read-only. Suspicious processes: flag, do NOT kill.