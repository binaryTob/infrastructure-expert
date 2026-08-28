---
id: "docker_secrets_analysis"
name: "Docker Secrets Exposure Analysis"
version: "1.0"
category: "security"
phase: "forensic"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "docker_analysis"]
triggers: ["PRESENT:docker"]
provides: ["container_env_secrets", "secret_mounts", "privileged_containers"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/docker-secrets" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Docker Secrets Exposure Analysis

## Objective
Investigate how secrets (.env, credentials, tokens) are exposed through Docker
containers: environment variables, volume mounts, Docker socket exposure,
privileged mode, and Docker Swarm secrets.

## Commands

### 1. Environment variables with secrets in all containers
```bash
# [risk:ro] [mode:auto] [requires:docker]
ssh {{SSH_TARGET}} 'docker ps --format "{{.ID}} {{.Names}}" 2>/dev/null | while read id name; do
  echo "=== CONTAINER: $name ($id) ==="
  docker inspect "$id" --format "{{range .Config.Env}}{{.}}{{\"\n\"}}{{end}}" 2>/dev/null | grep -iE "KEY|SECRET|TOKEN|PASSWORD|DATABASE_URL|API|GITHUB|GIT|PASS|CREDENTIAL|AUTH" || echo "(no secret-pattern env vars)"
done'
```

### 2. Volume mounts audit
```bash
# [risk:ro] [mode:auto] [requires:docker]
ssh {{SSH_TARGET}} 'docker ps --format "{{.ID}} {{.Names}}" 2>/dev/null | while read id name; do
  echo "=== MOUNTS: $name ==="
  docker inspect "$id" --format "{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}} (RW={{.RW}}){{\"\n\"}}{{end}}" 2>/dev/null
done'
```

### 3. .env files mounted into containers
```bash
# [risk:ro] [mode:auto] [requires:docker]
ssh {{SSH_TARGET}} 'echo "=== CONTAINERS WITH .ENV MOUNTS ==="; docker ps -q 2>/dev/null | while read id; do
  name=$(docker inspect "$id" --format "{{.Name}}" 2>/dev/null)
  docker inspect "$id" --format "{{range .Mounts}}{{.Source}}{{\"\n\"}}{{end}}" 2>/dev/null | grep -iE "\.env|secret|credential|token|password|key" && echo "[ALERT] Secret-related mount in: $name ($id)"
done'
```

### 4. Docker socket exposure
```bash
# [risk:ro] [mode:auto] [requires:docker]
ssh {{SSH_TARGET}} 'echo "=== DOCKER SOCKET MOUNTS ==="; docker ps -q 2>/dev/null | while read id; do
  name=$(docker inspect "$id" --format "{{.Name}}" 2>/dev/null)
  docker inspect "$id" --format "{{range .Mounts}}{{.Source}}{{\"\n\"}}{{end}}" 2>/dev/null | grep -q "docker.sock" && echo "[CRITICAL] docker.sock mounted in: $name ($id)"
done; echo; echo "=== DOCKER SOCKET PERMISSIONS ==="; ls -la /var/run/docker.sock 2>/dev/null'
```

### 5. Privileged containers
```bash
# [risk:ro] [mode:auto] [requires:docker]
ssh {{SSH_TARGET}} 'echo "=== PRIVILEGED CONTAINERS ==="; docker ps -q 2>/dev/null | while read id; do
  priv=$(docker inspect "$id" --format "{{.HostConfig.Privileged}}" 2>/dev/null)
  name=$(docker inspect "$id" --format "{{.Name}}" 2>/dev/null)
  [ "$priv" = "true" ] && echo "[CRITICAL] PRIVILEGED: $name ($id)"
done; echo; echo "=== HOST PID/NET MODE ==="; docker ps -q 2>/dev/null | while read id; do
  name=$(docker inspect "$id" --format "{{.Name}}" 2>/dev/null)
  pid=$(docker inspect "$id" --format "{{.HostConfig.PidMode}}" 2>/dev/null)
  net=$(docker inspect "$id" --format "{{.HostConfig.NetworkMode}}" 2>/dev/null)
  [ "$pid" = "host" ] && echo "[CRITICAL] host PID namespace: $name"
  [ "$net" = "host" ] && echo "[HIGH] host network mode: $name"
done'
```

### 6. Docker secrets (Swarm)
```bash
# [risk:ro] [mode:auto] [requires:docker]
ssh {{SSH_TARGET}} 'echo "=== DOCKER SECRETS (SWARM) ==="; docker secret ls 2>/dev/null || echo "Docker Swarm not active"; echo; echo "=== DOCKER CONFIGS ==="; docker config ls 2>/dev/null || echo "Docker Swarm not active"'
```

### 7. docker-compose files with env_file references
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== DOCKER-COMPOSE FILES ==="; find / -name "docker-compose*.yml" -o -name "docker-compose*.yaml" -o -name "compose.yml" -o -name "compose.yaml" 2>/dev/null | head -20 | while read f; do
  echo "FILE: $f ($(stat -c "%a %U:%G" "$f" 2>/dev/null))"
  grep -nE "env_file|environment:|secrets:" "$f" 2>/dev/null | head -10
  echo
done'
```

### 8. Docker daemon configuration
```bash
# [risk:ro] [mode:auto] [requires:docker]
ssh {{SSH_TARGET}} 'echo "=== DOCKER DAEMON CONFIG ==="; cat /etc/docker/daemon.json 2>/dev/null || echo "No daemon.json"; echo; echo "=== DOCKER VERSION ==="; docker version --format "{{.Server.Version}}" 2>/dev/null; echo; echo "=== DOCKER INFO (security) ==="; docker info --format "Security Options: {{.SecurityOptions}}" 2>/dev/null'
```

### 9. Container user audit (running as root?)
```bash
# [risk:ro] [mode:auto] [requires:docker]
ssh {{SSH_TARGET}} 'echo "=== CONTAINERS RUNNING AS ROOT ==="; docker ps -q 2>/dev/null | while read id; do
  name=$(docker inspect "$id" --format "{{.Name}}" 2>/dev/null)
  user=$(docker inspect "$id" --format "{{.Config.User}}" 2>/dev/null)
  [ -z "$user" ] || [ "$user" = "root" ] || [ "$user" = "0" ] && echo "ROOT: $name (User=${user:-default})"
done'
```

### 10. Docker events (recent secret-related activity)
```bash
# [risk:ro] [mode:auto] [requires:docker]
ssh {{SSH_TARGET}} 'echo "=== DOCKER EVENTS LAST 24H ==="; docker events --since 24h --format "{{.Time}} {{.Type}} {{.Action}} {{.Actor.Attributes.name}}" 2>/dev/null | tail -30'
```

## Analysis

### Severity mapping
| Finding | Severity | Confidence |
|---------|----------|------------|
| docker.sock mounted in container | CRITICAL | HIGH |
| Container --privileged | CRITICAL | HIGH |
| .env file mounted as volume | HIGH | HIGH |
| Container with host PID namespace | CRITICAL | HIGH |
| Container with host network mode | MEDIUM | HIGH |
| Secrets in env vars (visible via inspect) | MEDIUM | HIGH |
| Container running as root without user namespace | MEDIUM | HIGH |
| docker-compose.yml world-readable with env_file | MEDIUM | MEDIUM |
| Docker Swarm secrets in use | INFO (good) | HIGH |

### Correlation
- Cross-reference with `credential_exposure_analysis` for .env files that are mounted
- Cross-reference with `network_exfiltration` for containers with outbound connections
- Cross-reference with `git_credential_analysis` for git operations inside containers

## Evidence
- `docker-env-secrets.yml` — env vars containing secret patterns
- `docker-mounts.yml` — volume mounts per container
- `docker-privileged.yml` — privileged/host-mode containers
- `docker-compose-files.yml` — compose files with env references

## False Positives
- Docker secrets (Swarm) are the SECURE way to handle secrets — report as INFO
- env_file referencing .env but the .env is not in a git repo and has restricted perms
- Container running as root by design (official images like nginx need it for port binding)
- docker-compose.yml with `env_file` where the .env is properly restricted

## Security
Read-only. Never output actual secret values from env vars. Only report:
- Variable name (e.g., DATABASE_URL, not the value)
- Mount source path and permissions
- Container name, ID, and security context
All output must pass through `scripts/redact.sh`.
