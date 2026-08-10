---
id: "system_inventory"
name: "System Inventory"
version: "2.0"
category: "discovery"
phase: "discover"
risk: "readonly"
execution_mode: "auto"
depends_on: []
provides: ["os", "kernel", "uptime", "cpu_topology", "memory_total", "disk_topology", "net_ifaces"]
triggers: []
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/discovery" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# System Inventory

Entry point. Broad, cheap, read-only discovery of the host's real architecture.
No assumptions. Run first, always.

This skill is TRIAGE-ONLY. It does a one-line check per dimension and defers
full analysis to specialized skills:
- Services/timers/sockets -> `systemd_analysis` (owns all systemctl calls)
- Network details -> `network_analysis`
- Disk details -> `disk_analysis`
- Docker -> `docker_analysis`
- Kubernetes -> `kubernetes_analysis`

## Commands

### OS / kernel / arch / uptime
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'uname -a; hostnamectl 2>/dev/null; cat /etc/os-release 2>/dev/null; uptime; date'
```

### CPU / RAM (triage only — full analysis in cpu_analysis/memory_analysis)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'nproc; lscpu 2>/dev/null | head -5; free -h; cat /proc/loadavg'
```

### Disk topology (triage only — full analysis in disk_analysis)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT 2>/dev/null; echo ===; df -hT -x tmpfs -x devtmpfs 2>/dev/null | head -10'
```

### Init system
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ps -p 1 -o pid,comm,args --no-headers; file /sbin/init 2>/dev/null'
```

### Users & privilege surface (names only)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'awk -F: '"'"'($3==0){print "root-equiv:"$1} ($7 ~ /sh$/){print "shell:"$1":"$7} ($2=="!"){print "locked:"$1} ($2==""){print "no-passwd:"$1}'"'"' /etc/passwd 2>/dev/null; echo ===; getent passwd | awk -F: '"'"'{print $1":"$3":"$6":"$7}'"'"'; echo ===; getent group | sort'
```

### Network triage (one-liner only — full analysis in network_analysis)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ip -br addr 2>/dev/null; echo ===; ip route 2>/dev/null | head -5'
```

### Detection of runtimes / orchestrators / ingress / DB / WAF / observability
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for b in docker docker-compose containerd ctr crictl nerdctl kubectl k3s kubeadm k0s helm kustomize podman runc nginx httpd apache2 haproxy traefik caddy envoy cilium calico flannel modsec openappsec postgres psql mysql mariadbd redis-server redis-cli mongod rabbitmqctl elasticsearch prometheus grafana loki vector fluent-bit fluentd jaeger node_exporter cadvisor fail2ban-client; do p=$(command -v $b 2>/dev/null); [ -n "$p" ] && echo "PRESENT:$b -> $p"; done; echo ===; ss -H -tlnp 2>/dev/null | awk '"'"'{print $4}'"'"' | sort -u | head -30'
```

### Config locations probe (existence only, NOT full dump)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for d in /etc/nginx /etc/traefik /etc/apache2 /etc/httpd /etc/haproxy /etc/kubernetes /etc/rancher /etc/systemd/system /opt /srv /var/www /usr/local/bin /root/.kube; do [ -e "$d" ] && echo "EXISTS $d"; done'
```

### Kubernetes presence check (1 command only — full analysis in kubernetes_analysis)
```bash
# [risk:ro] [mode:auto] [requires:kubectl]
ssh {{SSH_TARGET}} 'kubectl get nodes -o wide 2>/dev/null || echo "kubectl no disponible"'
```

## Analysis
Build the inventory from detected technologies. Feed `present_tech` into skill selection.
- Empty `docker ps` does NOT mean "no docker" — check the binary + socket.
- `kubectl get ...` returning empty/Connection refused means "no accessible kubeconfig", not necessarily "no cluster".
- Cron jobs are NOT scanned here — `backup_analysis` and `systemd_analysis` own those.

## Evidence produced
- `os.txt`, `cpu.txt`, `ram.txt`, `disk.txt`, `init.txt`, `users.txt`, `net-triage.txt`, `detected.txt`, `config-paths.txt`, `k8s-presence.txt`

## Security
Read-only. Redact secrets with `helpers.redact` before storing.