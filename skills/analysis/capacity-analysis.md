---
id: "capacity_analysis"
name: "Capacity Analysis"
version: "1.0"
category: "capacity"
phase: "correlate"
risk: "readonly"
execution_mode: "auto"
depends_on:
  - "cpu_analysis"
  - "memory_analysis"
  - "disk_analysis"
  - "io_analysis"
  - "network_analysis"
provides: ["capacity_buckets", "trend", "headroom"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/capacity" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Capacity Analysis

## Objective
Correlate all resource dimensions into a unified capacity view: what is near its limit, what has headroom, what is trending toward saturation.

## What it does
This skill does NOT execute new commands. It reads evidence from cpu, memory, disk, io, and network analyses and produces a unified capacity assessment with:
- Per-axis bucket (NORMAL/WATCH/WARNING/CRITICAL)
- Trend (stable/improving/degrading)
- Headroom estimation (days/weeks/months until saturation)
- Cross-axis correlations (e.g., high CPU = memory pressure due to swapping)

## Capacity buckets (per axis)

| Axis | NORMAL | WATCH | WARNING | CRITICAL |
|------|--------|-------|---------|----------|
| CPU | load/nproc < 0.7 | 0.7-1.0 | 1.0-2.0 | > 2.0 |
| Memory | avail > 25% | 10-25% | 5-10% | < 5% |
| Disk | use < 70% | 70-85% | 85-95% | > 95% |
| I/O | %iowait < 5 | 5-15 | 15-30 | > 30 |
| Network | conns < 50% max | 50-80% | 80-95% | > 95% |

## Trend interpretation (from temporal series)
- **Stable**: metrics oscillate within normal range.
- **Improving**: metric moving toward NORMAL (e.g., load decreasing after spike).
- **Degrading**: metric moving away from NORMAL (e.g., memory available decreasing monotonically).
- **Fluctuating**: high variance without clear direction. Requires longer observation.

## Headroom estimation
- CPU: `1 - (current_load/nproc_ratio)` then project with trend slope.
- Memory: `(available - 10%_buffer) / rate_of_decrease`.
- Disk: `(free_space / daily_growth)` if growth rate can be inferred from `lsof` or log consumption.

## Cross-axis correlations
- High %iowait + high %wa in CPU: I/O is bottleneck, not CPU.
- High swap usage + high load: memory pressure spilling into CPU (thrashing).
- Low available memory + growing disk usage: swap/thin provisioning risk.

## Output
- `capacity-assessment.md` (Narrative).
- `findings.yaml` entries for each WARNING/CRITICAL axis.

## Security
Read-only (correlation of existing evidence).
