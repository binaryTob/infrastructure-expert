---
id: "docker_troubleshooting"
name: "Docker Troubleshooting"
version: "1.0"
category: "docker"
phase: "diagnose"
risk: "readonly"
execution_mode: "auto"
depends_on: ["docker_analysis"]
triggers: ["PRESENT:docker"]
provides: ["container_exit_codes", "container_health_status", "container_restart_policies", "container_dns_config", "docker_events_detail"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/docker" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "yml", schema: "output_schema" }
---
# Docker Troubleshooting

## Objective
Deep inspection of container health, exit codes, restart policies, DNS configuration,
OOM kills, and Docker events. Identifies why containers are failing, what signal killed
them, whether they have health checks, and why they aren't restarting.

## Commands

### Exited containers analysis (exit codes + OOM + timing)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== EXITED CONTAINERS ==="; docker ps -a --filter "status=exited" --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null; echo; echo "=== EXIT CODE + OOM ANALYSIS ==="; for c in $(docker ps -a --filter "status=exited" -q 2>/dev/null); do name=$(docker inspect --format "{{.Name}}" $c | cut -c2-); exit=$(docker inspect --format "{{.State.ExitCode}}" $c); started=$(docker inspect --format "{{.State.StartedAt}}" $c); finished=$(docker inspect --format "{{.State.FinishedAt}}" $c); oom=$(docker inspect --format "{{.State.OOMKilled}}" $c); echo "NAME=$name EXIT=$exit OOM=$oom STARTED=$started FINISHED=$finished"; done'
```

### Container restart policies
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for c in $(docker ps -q 2>/dev/null); do name=$(docker inspect --format "{{.Name}}" $c | cut -c2-); restart=$(docker inspect --format "{{.HostConfig.RestartPolicy.Name}}" $c); echo "$name restart=$restart"; done | sort'
```

### Container health status
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for c in $(docker ps -q 2>/dev/null); do name=$(docker inspect --format "{{.Name}}" $c | cut -c2-); health=$(docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $c); echo "$name health=$health"; done | sort'
```

### DNS configuration per container
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== DOCKER DAEMON DNS ==="; cat /etc/docker/daemon.json 2>/dev/null || echo "no-daemon-json"; echo; echo "=== HOST RESOLV ==="; cat /etc/resolv.conf; echo; echo "=== CONTAINER DNS (sample 5) ==="; for c in $(docker ps -q 2>/dev/null | head -5); do name=$(docker inspect --format "{{.Name}}" $c | cut -c2-); dns=$(docker exec $c cat /etc/resolv.conf 2>/dev/null | grep nameserver | tr "\n" " "); echo "$name -> $dns"; done'
```

### DNS test from containers
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== HOST DNS TEST ==="; nslookup google.com 2>&1 | head -3; echo; echo "=== CONTAINER DNS TEST (sample 3) ==="; for c in $(docker ps -q 2>/dev/null | head -3); do name=$(docker inspect --format "{{.Name}}" $c | cut -c2-); result=$(docker exec $c nslookup google.com 2>&1 | head -3 || echo "nslookup-failed"); echo "$name: $result"; done'
```

### Docker events (last 1h)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'docker events --since 1h --until now --filter type=container --format "{{.Time}} {{.Type}} {{.Action}} {{.Actor.Attributes.name}}" 2>/dev/null | tail -30'
```

### Docker networks + subnet mapping
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'docker network ls 2>/dev/null; echo; for net in $(docker network ls -q 2>/dev/null); do docker network inspect $net --format "{{.Name}} driver={{.Driver}} subnet={{range .IPAM.Config}}{{.Subnet}} {{end}}" 2>/dev/null; done'
```

## Analysis
- **Exit 137 (SIGKILL)**: OOM kill or `docker kill`. Check OOMKilled flag in inspect.
- **Exit 143 (SIGTERM)**: Normal termination (`docker stop`). Cross-reference with events.
- **Exit 1/Non-zero**: Application error. Check `docker logs` for the container.
- **EAI_AGAIN in DNS**: Temporary DNS failure or unreachable nameserver. Check resolv.conf.
- **nameserver 100.100.100.100**: Tailscale MagicDNS residue. Container can't reach it.
- **health=none for most containers**: No automatic recovery. Implement HEALTHCHECK.
- **restart=no**: Container won't recover from crash or Docker restart.

## False Positives
- "Container exit=0 OOM=true" — OOMKilled flag can be true even for clean exit (kernel flag).

## Thresholds
| Metric | NORMAL | WARNING | CRITICAL |
|--------|--------|---------|----------|
| Exited containers with restart=no | 0 | 1-2 | >2 |
| Containers without health check (in prod) | 0% | <50% | >50% |
| Containers with restart=no (in prod) | 0 | <10% | >10% |
| DNS nameserver != host DNS | 0 | 1 | >1 |

## Evidence
- `docker-exited.yml`, `docker-restart.yml`, `docker-health.yml`, `docker-dns.yml`, `docker-events.yml`, `docker-networks.yml`

## Security
Read-only. Never `docker rm`, `docker kill`, or `docker restart` automatically.