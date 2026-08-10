---
id: "cpu_analysis"
name: "CPU Analysis"
version: "1.0"
category: "cpu"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
provides: ["load_avg", "cpu_per_process", "cpu_trend"]
triggers: []
false_positives:
  - "CPU alta durante backups/cron windows: correlar con timers activos antes de concluir."
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/cpu" }
  SSH_TARGET: { type: "string", required: true }
  SAMPLE_INTERVAL: { type: "duration", default: "30s" }
  SAMPLE_COUNT: { type: "integer", default: "4" }
output: { format: "json", schema: "output_schema" }
---
# CPU Analysis

## Objective
Determine load avg vs nproc, top processes by CPU, temporal trend, runaway/loops and oversized workers.

## Commands

### Load + uptime + context
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== LOAD/UP ==="; uptime; echo; echo "=== nproc ==="; nproc; echo; echo "=== /proc/loadavg ==="; cat /proc/loadavg'
```

### Top processes by CPU
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ps -eo pid,ppid,user,pcpu,pmem,etime,comm,args --sort=-pcpu | head -25'
```

### Temporal load series (snapshots, no artificial load)
```bash
# [risk:probe] [mode:auto]
for i in $(seq 0 {{SAMPLE_COUNT}}); do
  { echo "T$i $(date -u +%T)"; ssh {{SSH_TARGET}} 'cat /proc/loadavg; vmstat 1 2 2>/dev/null | tail -1'; echo "---"; } >> {{OUTPUT_DIR}}/trend.txt
  [ "$i" -lt "{{SAMPLE_COUNT}}" ] && sleep {{SAMPLE_INTERVAL}}
done
```

### Per-CPU (if mpstat available)
```bash
# [risk:ro] [mode:auto] [requires:mpstat]
ssh {{SSH_TARGET}} 'mpstat -P ALL 1 1 2>/dev/null || echo "mpstat ausente"'
```

### pidstat per process
```bash
# [risk:ro] [mode:auto] [requires:pidstat]
ssh {{SSH_TARGET}} 'pidstat -u 1 2 2>/dev/null | sort -k8 -nr | head -20 || true'
```

## Analysis
- `load_avg/nproc`: > 1 -> saturation; trend > 0 -> degradation. Combine with `%wa` from vmstat.
- Top process with `%CPU > 100/nproc` and long `etime` -> current: investigate comm/args.
- Series `r` (running) steady > nproc -> CPU bottleneck. Stable low series -> NORMAL.
- High `%system` with low `%user` -> suspect kernel/driver/io.

## Thresholds
| Metric | NORMAL | WATCH | WARNING | CRITICAL |
|--------|--------|-------|---------|----------|
| load/nproc | < 0.7 | 0.7-1.0 | 1.0-2.0 | > 2.0 |
| %user (1m) | < 50 | 50-70 | 70-85 | > 85 |
| %iowait | < 5 | 5-15 | 15-30 | > 30 |

## Security
Read-only. If top process is miner (xmrig, kdevtmpfsi, kinsing): FLAG -> `security_analysis`; do not kill.
