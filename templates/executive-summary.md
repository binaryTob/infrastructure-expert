# Executive Summary — {{SERVER_NAME}}

**Generado:** {{DATE}}  ·  **Host:** {{HOSTNAME}}  ·  **Espec SSH:** {{SSH_TARGET}}  ·  **Read-only**

---

## Sistema

| | |
|---|---|
| **OS**        | {{OS}} |
| **Kernel**    | {{KERNEL}} |
| **Uptime**    | {{UPTIME}} |
| **CPU**       | {{CPU_MODEL}} ({{NPROC}} nucleos · {{CPU_ARCH}}) |
| **RAM**       | {{RAM_TOTAL}} (available {{RAM_AVAIL_PCT}}%) |
| **Swap**      | {{SWAP_TOTAL}} (used {{SWAP_USED_PCT}}%) |
| **Storage**   | {{DISK_SUMMARY}} |
| **Containers**| {{CONTAINER_COUNT}} running (Docker {{DOCKER_VERSION}} / K8s {{K8S_VERSION}}) |
| **Services**  | {{SVC_RUNNING}} running · {{SVC_ENABLED}} enabled · {{SVC_FAILED}} failed |

---

## Overall Health

> {{OVERALL_BUCKET}} — {{OVERALL_TREND}}

| Axis | Bucket | Trend | Nota |
|------|--------|-------|------|
| CPU     | {{CPU_BUCKET}} | {{CPU_TREND}} | {{CPU_NOTE}} |
| Memory  | {{MEM_BUCKET}} | {{MEM_TREND}} | {{MEM_NOTE}} |
| Disk    | {{DISK_BUCKET}} | {{DISK_TREND}} | {{DISK_NOTE}} |
| I/O     | {{IO_BUCKET}} | {{IO_TREND}} | {{IO_NOTE}} |
| Network | {{NET_BUCKET}} | {{NET_TREND}} | {{NET_NOTE}} |

Leyenda: `NORMAL` · `WATCH` · `WARNING` · `CRITICAL`

---

## Hallazgos por prioridad

| P0 Critical | P1 High | P2 Medium | P3 Low | P4 Info |
|-------------|---------|-----------|--------|---------|
| {{P0_COUNT}} | {{P1_COUNT}} | {{P2_COUNT}} | {{P3_COUNT}} | {{P4_COUNT}} |

---

## Recommended Actions (orden)

1. {{ACTION_1}} — prioridad {{P1}}, riesgo {{RISK_1}}, esfuerzo {{EFFORT_1}}
2. {{ACTION_2}}
3. {{ACTION_3}}

> El detalle completo esta en el reporte HTML generado.
> Ningun cambio fue aplicado al servidor. Este analisis fue **read-only**.
