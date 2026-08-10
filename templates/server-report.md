# Server Health Report — {{HOSTNAME}}

**Fecha:** {{DATE}}  ·  **Espec SSH:** {{SSH_TARGET}}  ·  **Read-only**

---

## 1. System overview
{{SYSTEM_OVERVIEW}}

## 2. Hardware
- CPU: {{CPU_TOPOLOGY}}
- RAM: {{RAM_DETAIL}}
- Disk topology: {{DISK_TOPOLOGY}}
- Network interfaces: {{NET_IFACES}}

## 3. Operating system
{{OS_DETAIL}}

## 4. CPU
- nproc: {{NPROC}} · load avg: {{LOADAVG}} · ratio load/nproc: {{LOAD_RATIO}}
- %user / %system / %iowait (1m): {{CPU_US}} / {{CPU_SY}} / {{CPU_WA}}
- trend: {{CPU_TREND}}
- top procesos: {{TOP_CPU_TABLE}}

## 5. Memory
- total/used/available/cache+buffers: {{MEM_TABLE}}
- swap: {{SWAP_DETAIL}}
- swappiness: {{SWAPPINESS}}
- PSI: {{PSI_DETAIL}}
- OOM historicos: {{OOM_DETAIL}}

## 6. Storage
{{STORAGE_TABLE}}

## 7. I/O
{{IO_TABLE}}

## 8. Processes
{{PROCESS_TABLE}}

## 9. Services
{{SERVICE_TABLE}}

## 10. Docker
{{DOCKER_SECTION}}

## 11. Kubernetes
{{K8S_SECTION}}

## 12. Networking
{{NETWORK_SECTION}}

## 13. Logs
{{LOGS_SECTION}}

## 14. Configuration
{{CONFIG_SECTION}}

## 15. Security observations
{{SECURITY_SECTION}}

## 16. Capacity
{{CAPACITY_SECTION}}

## 17. Findings
Resumen por prioridad:
| P0 | P1 | P2 | P3 | P4 |
|----|----|----|----|----|
| {{P0}} | {{P1}} | {{P2}} | {{P3}} | {{P4}} |

Ver `findings.md` para el detalle con evidencia, analisis, recomendacion, validacion y rollback.
