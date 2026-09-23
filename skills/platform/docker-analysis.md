---
id: "docker_analysis"
name: "Docker Analysis"
version: "1.0"
category: "docker"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
triggers: ["PRESENT:docker"]
provides: ["containers", "container_stats", "container_state_limits", "images", "volumes"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/docker" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Docker Analysis

## Objective
Inventory running containers, resources, images, volumes, limits, and events.

## Commands

### Container inventory
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== PS ==="; docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null; echo; echo "=== ALL ==="; docker ps -a --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null'
```

### Container stats
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" 2>/dev/null'
```

### Container state and limits (single inspect pass)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ids=$(docker ps -aq 2>/dev/null); [ -n "$ids" ] && docker inspect --format "name={{.Name}} status={{.State.Status}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}} restarts={{.RestartCount}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} restart_policy={{.HostConfig.RestartPolicy.Name}} mem_limit={{.HostConfig.Memory}} mem_swap={{.HostConfig.MemorySwap}} cpu_nano={{.HostConfig.NanoCpus}} started={{.State.StartedAt}} finished={{.State.FinishedAt}}" $ids || echo "no-containers"'
```

### Docker info
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'docker info --format "Server={{.ServerVersion}} driver={{.Driver}} cpus={{.NCPU}} mem={{.MemTotal}} containers={{.Containers}} running={{.ContainersRunning}} paused={{.ContainersPaused}} stopped={{.ContainersStopped}} images={{.Images}}" 2>/dev/null'
```

### Image inventory
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" 2>/dev/null | head -50'
```

### Disk usage
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'docker system df 2>/dev/null; echo; echo "=== VOLUMES ==="; docker volume ls 2>/dev/null'
```

### Docker events (last 50)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'docker events --since 24h --until now --filter type=container 2>/dev/null | tail -50 || echo "no events"'
```

## Analysis
- Non-zero exit or OOM kill emits `CONDITION:docker_container_failed`.
- Restart count above the contextual baseline emits `CONDITION:docker_restart_loop`.
- Health status `unhealthy` emits `CONDITION:docker_health_unhealthy`.
- Containers without memory limit: OOM risk under pressure.
- Zero CPU limit: container can use all available CPU.
- Running > 20 containers on a small machine: check resource distribution.
- `docker system df` with `Build Cache > 1GB`: reclaimable space.
- Old images (> 30 days, not in use): candidate for cleanup (Level 3).

## Evidence
- `containers.txt`, `stats.txt`, `state-limits.txt`, `info.txt`, `images.txt`, `disk-df.txt`, `events.txt`

## Security
Read-only. Never `docker rm` or `docker prune`.
