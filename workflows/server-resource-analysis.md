# Workflow: Server Resource Analysis

Flujo enfocado en analisis de recursos y performance de servidores Linux.
Read-only, reusable contra cualquier servidor.

## Diagrama

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

## Modos de ejecucion

| Modo | Skills | Cuando |
|------|--------|--------|
| `full` | 22 | Analisis completo |
| `quick` | 6 | Triage rapido (inventario + CPU/mem/disk/io + logs) |
| `container` | 6 | Host de contenedores (Docker + K8s + process + net + capacity) |

## Segunda ejecucion (post-optimizacion)

```
BASELINE (reportes/run-1/)
  aplicar cambios (externo, con aprobacion)
POST-OPTIMIZATION (reportes/run-2/)
COMPARISON (optimization-comparison.md)
```
