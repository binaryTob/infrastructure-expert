---
id: "memory_analysis"
name: "Memory Analysis"
version: "2.0"
category: "memory"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
provides: ["mem_usage", "swap", "mem_per_process", "psi"]
triggers: []
false_positives:
  - "used~=total sin presion real si cache+buffers alto y available holgada -> NORMAL."
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/memory" }
  SSH_TARGET: { type: "string", required: true }
  SAMPLE_INTERVAL: { type: "duration", default: "30s" }
  SAMPLE_COUNT: { type: "integer", default: "4" }
output: { format: "json", schema: "output_schema" }
---
# Memory Analysis

Interpret RAM/swap correctly (available vs used vs cache/buffers), detect real memory
pressure, leaks, and live PSI. This skill OWNS the live-memory view (free, meminfo, PSI,
per-process RSS, swap trend).

OOM-in-logs detection has been moved to `log_analysis` (owns all kernel log greps).
This avoids byte-identical `dmesg -T | grep oom` being executed twice per audit.

## Commands

### Current memory
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== FREE ==="; free -h; echo; echo "=== MEMINFO ==="; grep -E "MemTotal|MemFree|MemAvailable|Buffers|Cached|SwapTotal|SwapFree|Slab|CommitLimit|Committed_AS" /proc/meminfo; echo; echo "=== SWAPPINESS ==="; cat /proc/sys/vm/swappiness'
```

### Top processes by memory (RSS)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ps -eo pid,ppid,user,rss,vsz,pmem,comm,args --sort=-rss | head -25; echo; echo "=== smem (if exists) ==="; command -v smem >/dev/null && smem -t -k | tail -30 || echo "smem ausente"'
```

### Swap/available trend series
```bash
# [risk:probe] [mode:auto]
for i in $(seq 0 {{SAMPLE_COUNT}}); do
  { echo "T$i $(date -u +%T)"; ssh {{SSH_TARGET}} 'awk "/SwapTotal|SwapFree|MemAvailable/{print}" /proc/meminfo'; } >> {{OUTPUT_DIR}}/trend.txt
  sleep {{SAMPLE_INTERVAL}}
done
```

### /proc/pressure/memory (PSI) if exists
```bash
# [risk:ro] [mode:auto] [requires:PSI]
ssh {{SSH_TARGET}} 'cat /proc/pressure/memory 2>/dev/null || echo "PSI mem ausente"'
```

## Analysis
- `available` low (< 10% total) AND swap free decreasing -> real pressure.
- `SwapTotal>0` and `SwapFree` continuously decreasing -> active swapping -> WARNING/CRITICAL.
- PSI `some > 50` or `full > 10` -> confirmed pressure (HIGH confidence).
- RSS monotonically growing in the series -> possible leak.
- `Committed_AS > CommitLimit` -> dangerous overcommit.
- For historical OOM events: read `logs/oom.txt` from `log_analysis` (owns log-based OOM detection).

## Thresholds
| Metric | NORMAL | WATCH | WARNING | CRITICAL |
|--------|--------|-------|---------|----------|
| mem available % | > 25% | 10-25% | 5-10% | < 5% |
| swap used % | < 10% | 10-30% | 30-50% | > 50% |
| PSI some avg10 | < 10 | 10-30 | 30-50 | > 50 |

## Security
Read-only.