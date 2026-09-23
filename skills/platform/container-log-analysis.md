---
id: "container_log_analysis"
name: "Container Log Analysis"
version: "1.0"
category: "docker"
phase: "diagnose"
risk: "readonly"
execution_mode: "auto"
depends_on: ["docker_analysis", "docker_troubleshooting"]
triggers: ["CONDITION:docker_container_failed", "CONDITION:docker_restart_loop", "CONDITION:docker_health_unhealthy", "SYMPTOM:container_failure"]
provides: ["container_error_logs", "container_crash_logs", "container_api_errors"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/docker" }
  SSH_TARGET: { type: "string", required: true }
  LOG_TAIL_LINES: { type: "integer", default: 50 }
  CONTAINER_IDS: { type: "string", required: true, description: "Space-separated IDs/names from Docker evidence; each must match ^[A-Za-z0-9_.-]+$" }
output: { format: "yml", schema: "output_schema" }
---
# Container Log Analysis

## Objective
Inspect bounded recent logs only from containers implicated by prior evidence. Detect
application errors, crashes, timeouts, DNS failures and API errors without scanning
unrelated workloads.

## Commands

### Error summary from implicated containers
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'for c in {{CONTAINER_IDS}}; do echo "=== $c ==="; docker logs --tail {{LOG_TAIL_LINES}} "$c" 2>&1 | grep -iE "error|fail|timeout|refused|unreachable|EAI_AGAIN|ENOTFOUND|ECONNREFUSED|500|502|503|504|SIGTERM|SIGKILL|OOM|cannot|could not|unable" | tail -10; done'
```

### Inspect specific container logs (full tail)
```bash
# [risk:probe] [mode:auto]
# Replace <container-name> with the target container discovered in the inventory.
ssh {{SSH_TARGET}} 'docker logs --tail {{LOG_TAIL_LINES}} <container-name> 2>&1'
```

Resource limits, restart counts, health and daemon inventory are consumed from
`docker_analysis` and `docker_troubleshooting`; do not query them again here.

## Analysis
- **Logs grep on error keywords**: Find failing dependency calls (EAI_AGAIN, ECONNREFUSED).
- **Memory limits = 0**: No limit configured. Container can consume all host RAM.
- **CPU nano = 0**: No CPU limit. Container can use all cores.
- **Restart counts > 5 in 24h**: Unstable container. Cross-reference with events.
- **Daemon DNS not configured**: Docker copies host resolv.conf (legacy mode) — vulnerable to host DNS changes (VPNs, Tailscale, systemd-resolved).

## Evidence
- `container-errors.yml`; resource/restart context is referenced from upstream evidence.

## Security
Read-only. Never modify container config automatically.
