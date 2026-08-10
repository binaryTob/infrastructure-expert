---
id: "systemd_analysis"
name: "Systemd Analysis"
version: "2.0"
category: "systemd"
phase: "discover"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
provides: ["services_running", "services_enabled", "services_failed", "timers", "unit_resources", "restart_counts", "timers_active"]
triggers: []
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/systemd" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Systemd Analysis

Skill unificado que combina el inventario de services (running/enabled/failed/timers/sockets)
con el analisis de recursos por unidad (MemoryCurrent, CPUUsageNSec, NRestarts, TasksCurrent).
Un solo skill evita ejecutar `systemctl list-units` 6 veces por auditoria.

## Comandos

### Running services (una sola vez)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'systemctl list-units --type=service --state=running --no-pager --no-legend 2>/dev/null'
```

### Enabled services
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'systemctl list-unit-files --type=service --state=enabled --no-pager --no-legend 2>/dev/null'
```

### Failed services
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'systemctl list-units --type=service --state=failed --no-pager --no-legend 2>/dev/null; echo ===; systemctl --failed --no-pager 2>/dev/null'
```

### Timers
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'systemctl list-timers --all --no-pager --no-legend 2>/dev/null'
```

### Sockets
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'systemctl list-units --type=socket --state=listening --no-pager --no-legend 2>/dev/null'
```

### Per-unit memory + tasks (cgroup)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for u in $(systemctl list-units --type=service --state=running --no-legend 2>/dev/null | awk "{print \$1}" | grep "\.service"); do mem=$(systemctl show "$u" -p MemoryCurrent 2>/dev/null | cut -d= -f2); tsk=$(systemctl show "$u" -p TasksCurrent 2>/dev/null | cut -d= -f2); echo "$u mem=${mem:-0} tasks=${tsk:-0}"; done | sort -t= -k2 -nr | head -20'
```

### Restart counts
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'systemctl list-units --type=service --state=running --no-legend 2>/dev/null | awk "{print \$1}" | while read u; do n=$(systemctl show "$u" -p NRestarts 2>/dev/null | cut -d= -f2); [ "${n:-0}" -gt 0 ] && echo "$u restarts=$n"; done'
```

### CPU per unit
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for u in $(systemctl list-units --type=service --state=running --no-legend 2>/dev/null | awk "{print \$1}"); do cpu=$(systemctl show "$u" -p CPUUsageNSec 2>/dev/null | cut -d= -f2); echo "$u cpu_ns=${cpu:-0}"; done | sort -t= -k2 -nr | head -15'
```

## Analysis
- `failed` > 0: flag failed service name, unit description, and exit code.
- `NRestarts > 5` in reasonable uptime: unstable service. Investigate journal logs (see `log_analysis`).
- `MemoryCurrent` consistently growing across snapshots: possible leak.
- Timer last activation far in the past but not triggered: disabled timer.
- Socket listening on 0.0.0.0: cross-reference with `network_analysis`.

## Evidence
- `running.txt`, `enabled.txt`, `failed.txt`, `timers.txt`, `sockets.txt`
- `unit-memory.txt`, `restarts.txt`, `unit-cpu.txt`

## Security
Read-only.