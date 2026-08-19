---
id: "reliability_analysis"
name: "Reliability Analysis"
version: "3.0"
category: "reliability"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "systemd_analysis"]
triggers: []
provides: ["ha_status", "spof_list", "storage_ha", "restart_analysis", "recovery_mechanisms"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/reliability" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Reliability Analysis

## Objective
Identify single points of failure (SPOF) and weak recovery mechanisms, on ANY host —
bare VM, Docker Compose, or Kubernetes. Does NOT assume Kubernetes. Works from
evidence already gathered by `system_inventory`, `systemd_analysis`, and (if present)
`docker_analysis` / `kubernetes_analysis`.

## Commands

### Host-level SPOF (runs always — non-K8s and K8s alike)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== FAILED UNITS ==="; systemctl list-units --type=service --state=failed 2>/dev/null; echo; echo "=== SWAP ==="; free -h | grep -i swap; echo; echo "=== FILESYSTEM REDUNDANCY ==="; lsblk -d -o NAME,TYPE,ROTA,SIZE 2>/dev/null; echo; echo "=== MDRAID / LVM ==="; cat /proc/mdstat 2>/dev/null || echo "no-mdraid"; pvs 2>/dev/null | head; echo; echo "=== UPTIME / REBOOTS ==="; uptime; last -x reboot shutdown 2>/dev/null | head -8'
```

### Docker restart policies + healthchecks (if docker present — non-K8s reliability)
```bash
# [risk:ro] [mode:auto] [requires:docker]
ssh {{SSH_TARGET}} 'for c in $(docker ps -a -q 2>/dev/null); do name=$(docker inspect --format "{{.Name}}" $c | cut -c2-); restart=$(docker inspect --format "{{.HostConfig.RestartPolicy.Name}}" $c); health=$(docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $c); rc=$(docker inspect --format "{{.RestartCount}}" $c); echo "$name restart=$restart health=$health restarts=$rc"; done | sort'
```

### Systemd unit restart config (runs always)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for u in $(systemctl list-units --type=service --state=running --no-legend 2>/dev/null | awk "{print \$1}" | head -40); do r=$(systemctl show "$u" -p Restart -p RestartSec --value 2>/dev/null | tr "\n" " "); echo "$u $r"; done'
```

### Kubernetes control plane (if k8s present — consumes kubernetes_analysis)
```bash
# [risk:ro] [mode:auto] [requires:kubectl]
ssh {{SSH_TARGET}} 'kubectl get pods -A 2>/dev/null | grep -E "etcd|kube-apiserver|kube-scheduler|kube-controller-manager" | awk "{print \$1, \$2}"; echo ===; kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints 2>/dev/null'
```

## Analysis

### Non-Kubernetes hosts
- **Single host = SPOF for everything** it runs. The exposure is the whole service stack on one machine; flag as MEDIUM/HIGH depending on criticality.
- **No swap** + memory-hungry services (Rails/Python/Node in dev mode) = OOM-kill risk under load; a single memory spike can silently kill a backend (e.g. a 502 whose upstream died).
- **`restart=no`** on containers = a crashed container stays down until a human notices. Recommend `restart=unless-stopped`.
- **`health=none`** on containers = no automatic liveness detection; Docker can't tell "up" from "hung".
- **`Restart=no`** systemd units (especially web servers/DBs) = no auto-recovery.
- **No RAID/LVM on a single data disk** = a disk failure is total data loss (no redundancy).
- **Failed units** present = something already broken and unrecovered.

### Kubernetes hosts
- Count etcd members: <3 = no HA; losing a single etcd node loses cluster state.
- Single control-plane node = API downtime on node loss.
- Ingress controller as DaemonSet on all nodes = good HA.
- CrashLoop for extended periods + no alerting = silent outage risk.

## False Positives
- `RestartCount` high right after a deploy/restart window is expected; correlate with `docker_analysis` events before flagging instability.
- A dev/staging box running with `restart=no` is often intentional — weight severity by whether the host serves production traffic.

## Evidence
- `host-spof.txt`, `docker-restart.txt`, `systemd-restart.txt`, `control-plane.txt`

## Security
Read-only. Never restart/enable units or change restart policies (Level 3).
