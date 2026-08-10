---
id: "io_analysis"
name: "I/O Analysis"
version: "1.0"
category: "io"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
provides: ["iostat", "vmstat_io", "io_wait", "io_per_process"]
triggers: []
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/io" }
  SSH_TARGET: { type: "string", required: true }
  SAMPLE_INTERVAL: { type: "duration", default: "30s" }
  SAMPLE_COUNT: { type: "integer", default: "4" }
output: { format: "json", schema: "output_schema" }
---
# I/O Analysis

## Objective
Detect I/O bottlenecks, high iowait, saturated devices, per-process I/O.

## Commands

### vmstat (includes io bi/bo)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'vmstat 1 3 2>/dev/null'
```

### iostat (if available)
```bash
# [risk:ro] [mode:auto] [requires:iostat]
ssh {{SSH_TARGET}} 'iostat -x 1 2 2>/dev/null || echo "iostat ausente"'
```

### iowait temporal series
```bash
# [risk:probe] [mode:auto]
for i in $(seq 0 {{SAMPLE_COUNT}}); do
  { echo "T$i $(date -u +%T)"; ssh {{SSH_TARGET}} 'cat /proc/stat | head -1; vmstat 1 2 2>/dev/null | tail -1'; } >> {{OUTPUT_DIR}}/trend.txt
  sleep {{SAMPLE_INTERVAL}}
done
```

### Per-process I/O (iotop or pidstat)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} '(command -v iotop >/dev/null && iotop -b -n 1 -o 2>/dev/null | head -25) || (command -v pidstat >/dev/null && pidstat -d 1 2 2>/dev/null | sort -k4 -nr | head -20) || echo "ni iotop ni pidstat disponibles"'
```

### /proc/diskstats
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'cat /proc/diskstats 2>/dev/null'
```

## Analysis
- `%iowait > 15%` sustained = WARNING. `> 30%` = CRITICAL.
- `await` (iostat) > 20ms on HDD or > 5ms on SSD: saturation.
- `%util` (iostat) > 90%: device saturated.
- Process with high `kB_rd/s` or `kB_wr/s`: cross-reference with `process_analysis`.

## Thresholds
| Metric | NORMAL | WATCH | WARNING | CRITICAL |
|--------|--------|-------|---------|----------|
| %iowait | < 5 | 5-15 | 15-30 | > 30 |
| await ms | < 10 | 10-20 | 20-50 | > 50 |
| %util | < 60 | 60-80 | 80-95 | > 95 |

## Security
Read-only.
