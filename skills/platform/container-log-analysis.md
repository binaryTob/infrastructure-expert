---
id: "container_log_analysis"
name: "Container Log Analysis"
version: "1.0"
category: "docker"
phase: "diagnose"
risk: "readonly"
execution_mode: "auto"
depends_on: ["docker_analysis", "docker_troubleshooting"]
triggers: ["PRESENT:docker"]
provides: ["container_error_logs", "container_crash_logs", "container_api_errors"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/docker" }
  SSH_TARGET: { type: "string", required: true }
  LOG_TAIL_LINES: { type: "integer", default: 50 }
output: { format: "yml", schema: "output_schema" }
---
# Container Log Analysis

## Objective
Inspect recent logs from ALL running containers to detect application-level errors,
crashes, timeouts, DNS failures, and API errors. Focuses on containers that are
running but potentially unhealthy.

## Commands

### Logs from all running containers (recent errors only)
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'for c in $(docker ps -q 2>/dev/null); do name=$(docker inspect --format "{{.Name}}" $c | cut -c2-); errors=$(docker logs --tail {{LOG_TAIL_LINES}} $c 2>&1 | grep -iE "error|fail|timeout|refused|unreachable|EAI_AGAIN|ENOTFOUND|ECONNREFUSED|500|502|503|504|SIGTERM|SIGKILL|OOM|cannot|could not|unable" | tail -5); [ -n "$errors" ] && echo "=== $name ===" && echo "$errors"; done'
```

### Inspect specific container logs (full tail)
```bash
# [risk:probe] [mode:auto]
# Replace <container-name> with the target container discovered in the inventory.
ssh {{SSH_TARGET}} 'docker logs --tail {{LOG_TAIL_LINES}} <container-name> 2>&1'
```

### Container resource limits (memory/CPU)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for c in $(docker ps -q 2>/dev/null); do name=$(docker inspect --format "{{.Name}}" $c | cut -c2-); mem=$(docker inspect --format "{{.HostConfig.Memory}}" $c); cpus=$(docker inspect --format "{{.HostConfig.NanoCpus}}" $c); mem_sw=$(docker inspect --format "{{.HostConfig.MemorySwap}}" $c); echo "$name mem_limit=${mem:-0} cpu_nano=${cpus:-0} mem_swap=${mem_sw:-0}"; done | sort'
```

### Docker daemon config
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== DAEMON.JSON ==="; cat /etc/docker/daemon.json 2>/dev/null || echo "no-daemon-json"; echo; echo "=== DOCKER VERSION ==="; docker version --format "{{.Server.Version}}" 2>/dev/null; echo; echo "=== DOCKER STORAGE ==="; docker system df -v 2>/dev/null | head -20'
```

### Container restart counts (instability indicator)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for c in $(docker ps -q 2>/dev/null); do name=$(docker inspect --format "{{.Name}}" $c | cut -c2-); rc=$(docker inspect --format "{{.RestartCount}}" $c); [ "$rc" -gt 0 ] && echo "$name restart_count=$rc"; done | sort -t= -k2 -nr'
```

## Analysis
- **Logs grep on error keywords**: Find failing dependency calls (EAI_AGAIN, ECONNREFUSED).
- **Memory limits = 0**: No limit configured. Container can consume all host RAM.
- **CPU nano = 0**: No CPU limit. Container can use all cores.
- **Restart counts > 5 in 24h**: Unstable container. Cross-reference with events.
- **Daemon DNS not configured**: Docker copies host resolv.conf (legacy mode) — vulnerable to host DNS changes (VPNs, Tailscale, systemd-resolved).

## Evidence
- `container-errors.yml`, `container-resources.yml`, `container-restart-counts.yml`

## Security
Read-only. Never modify container config automatically.