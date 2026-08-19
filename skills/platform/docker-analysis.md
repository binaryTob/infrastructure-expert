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
provides: ["containers", "container_stats", "images", "volumes", "container_limits"]
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

### Container limits
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for c in $(docker ps -q 2>/dev/null); do name=$(docker inspect --format "{{.Name}}" $c | cut -c2-); mem=$(docker inspect --format "{{.HostConfig.Memory}}" $c); cpus=$(docker inspect --format "{{.HostConfig.NanoCpus}}" $c); echo "$name mem_limit=${mem:-0} cpu_nano=${cpus:-0}"; done | sort'
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

### Exited containers detail (enhanced)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== EXITED ==="; docker ps -a --filter "status=exited" --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null; echo; echo "=== EXIT ANALYSIS ==="; for c in $(docker ps -a --filter "status=exited" -q 2>/dev/null); do name=$(docker inspect --format "{{.Name}}" $c | cut -c2-); exit=$(docker inspect --format "{{.State.ExitCode}}" $c); oom=$(docker inspect --format "{{.State.OOMKilled}}" $c); echo "$name exit=$exit OOM=$oom"; done'
```

## Analysis
- Containers without memory limit: OOM risk under pressure.
- Zero CPU limit: container can use all available CPU.
- Running > 20 containers on a small machine: check resource distribution.
- `docker system df` with `Build Cache > 1GB`: reclaimable space.
- Old images (> 30 days, not in use): candidate for cleanup (Level 3).

## Evidence
- `containers.txt`, `stats.txt`, `limits.txt`, `info.txt`, `images.txt`, `disk-df.txt`, `events.txt`

## Security
Read-only. Never `docker rm` or `docker prune`.
