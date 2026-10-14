# Executive Summary — {{SERVER_NAME}}

**Generated:** {{DATE}}  ·  **Host:** {{HOSTNAME}}  ·  **SSH target:** {{SSH_TARGET}}  ·  **Read-only**

---

## System

| | |
|---|---|
| **OS**        | {{OS}} |
| **Kernel**    | {{KERNEL}} |
| **Uptime**    | {{UPTIME}} |
| **CPU**       | {{CPU_MODEL}} ({{NPROC}} cores · {{CPU_ARCH}}) |
| **RAM**       | {{RAM_TOTAL}} (available {{RAM_AVAIL_PCT}}%) |
| **Swap**      | {{SWAP_TOTAL}} (used {{SWAP_USED_PCT}}%) |
| **Storage**   | {{DISK_SUMMARY}} |
| **Containers**| {{CONTAINER_COUNT}} running (Docker {{DOCKER_VERSION}} / K8s {{K8S_VERSION}}) |
| **Services**  | {{SVC_RUNNING}} running · {{SVC_ENABLED}} enabled · {{SVC_FAILED}} failed |

---

## Overall Health

> {{OVERALL_BUCKET}} — {{OVERALL_TREND}}

| Axis | Bucket | Trend | Note |
|------|--------|-------|------|
| CPU     | {{CPU_BUCKET}} | {{CPU_TREND}} | {{CPU_NOTE}} |
| Memory  | {{MEM_BUCKET}} | {{MEM_TREND}} | {{MEM_NOTE}} |
| Disk    | {{DISK_BUCKET}} | {{DISK_TREND}} | {{DISK_NOTE}} |
| I/O     | {{IO_BUCKET}} | {{IO_TREND}} | {{IO_NOTE}} |
| Network | {{NET_BUCKET}} | {{NET_TREND}} | {{NET_NOTE}} |

Legend: `NORMAL` · `WATCH` · `WARNING` · `CRITICAL`

---

## Findings by priority

| P0 Critical | P1 High | P2 Medium | P3 Low | P4 Info |
|-------------|---------|-----------|--------|---------|
| {{P0_COUNT}} | {{P1_COUNT}} | {{P2_COUNT}} | {{P3_COUNT}} | {{P4_COUNT}} |

---

## Recommended actions (in order)

1. {{ACTION_1}} — priority {{P1}}, risk {{RISK_1}}, effort {{EFFORT_1}}
2. {{ACTION_2}}
3. {{ACTION_3}}

> Full details are available in the generated HTML report.
> No changes were applied to the server. This analysis was **read-only**.
