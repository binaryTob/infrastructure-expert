# Workflow: Server Resource Analysis

Workflow focused on Linux server resource and performance analysis.
Read-only and reusable across servers.

## Diagram

```
PRE-FLIGHT CHECK (SSH reachable? tools present?)
  |
  v
SYSTEM DISCOVERY (system_inventory)
  |
  v
SYSTEMD ANALYSIS (systemd_analysis)
  |
  v
DETECT COMPONENTS (helpers.detect -> decide SKILL / SKIP)
  |
  v
RESOURCE ANALYSIS (cpu, memory, disk, io, process, network, systemd)
  |
  v
APPLICATION DISCOVERY (docker, kubernetes, database — conditional)
  |
  v
CONFIG + LOGS + SECURITY
  |
  v
CORRELATE (capacity_analysis)
  |
  v
OPTIMIZE (optimization_analysis)
  |
  v
FINDINGS + REPORT
```

## Execution modes

| Mode | Skills | When |
|------|--------|--------|
| `full` | 22 | Comprehensive analysis |
| `quick` | 6 | Rapid triage (inventory + CPU/memory/disk/I/O + logs) |
| `container` | 6 | Container host (Docker + K8s + processes + network + capacity) |

## Second run (post-optimization)

```
BASELINE (reportes/run-1/)
  apply changes (outside the framework, with approval)
POST-OPTIMIZATION (reportes/run-2/)
COMPARISON (optimization-comparison.md)
```
