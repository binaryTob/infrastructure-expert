---
name: system-discovery
area: discovery
description: Broad read-only discovery of a Linux host's real architecture (OS, init, users, services, network, runtimes, ingress, db, waf, observability).
purpose: Establish what actually exists on the host before any analysis skill runs. No assumptions.
safety: L1
prerequisites:
  - "SSH connectivity to host (evidence/<run-id>/00_connectivity.yml exists)"
applies_when:
  - "always (first skill)"
inputs:
  - "config/target.json"
discovery:
  # ── OS / kernel / arch / uptime
  - "uname -a; hostnamectl 2>/dev/null; cat /etc/os-release 2>/dev/null"
  - "uptime; date; timedatectl 2>/dev/null | head -10"
  # ── CPU / RAM / swap / load
  - "nproc; lscpu 2>/dev/null | head -25; free -h; cat /proc/loadavg"
  # ── disks / filesystems / mounts
  - "lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT 2>/dev/null; echo ===; df -hT -x tmpfs -x devtmpfs 2>/dev/null"
  - "findmnt --real 2>/dev/null | head -60"
  - "mount | grep -vE 'tmpfs|proc|sysfs|cgroup|devpts|mqueue|shm|fusectl' | head -40"
  # ── init system
  - "ps -p 1 -o pid,comm,args --no-headers; file /sbin/init 2>/dev/null"
  # ── users & privilege surface (names only, no hashes here)
  - "awk -F: '($3==0){print \"root-equivalent:\"$1} ($7 ~ /sh$/){print \"shell:\"$1\":\"$7} ($2==\"!\"){print \"locked:\"$1} ($2==\"\"){print \"no-passwd:\"$1}' /etc/passwd 2>/dev/null"
  - "getent passwd | awk -F: '{print $1\":\"$3\":\"$6\":\"$7}'"
  - "getent group | sort"
  - "sudo -ln 2>/dev/null | head -40"
  # ── services / timers / persistence
  - "systemctl list-units --type=service --state=running --no-pager --no-legend 2>/dev/null"
  - "systemctl list-unit-files --type=service --state=enabled --no-pager --no-legend 2>/dev/null | head -80"
  - "systemctl list-timers --all --no-pager --no-legend 2>/dev/null"
  - "systemctl list-units --type=socket --state=listening --no-pager --no-legend 2>/dev/null"
  - "ls -la /etc/cron* 2>/dev/null; echo ===; for f in /etc/crontab /etc/cron.d/* /etc/cron.daily/* /etc/cron.hourly/* /var/spool/cron/crontabs/*; do [ -f \"$f\" ] && echo \"--- $f ---\" && cat \"$f\"; done 2>/dev/null"
  - "ls -la /etc/rc.local /etc/profile.d/*.sh /etc/profile 2>/dev/null"
  # ── network: interfaces, routes, dns, gateway
  - "ip -br addr 2>/dev/null; echo ===; ip -o addr 2>/dev/null"
  - "ip route 2>/dev/null; echo ===; ip -6 route 2>/dev/null | head"
  - "cat /etc/resolv.conf 2>/dev/null; echo ===; cat /etc/hosts 2>/dev/null"
  # ── listening + established
  - "ss -H -tlnp 2>/dev/null; echo ===UDP===; ss -H -ulnp 2>/dev/null"
  - "ss -H -tnp state established 2>/dev/null | head -60"
  # ── firewall
  - "command -v ufw && ufw status verbose 2>/dev/null; command -v firewall-cmd && firewall-cmd --state 2>/dev/null; iptables -S 2>/dev/null | head -60; nft list ruleset 2>/dev/null | head -80"
  # ── detect runtimes/orchestrators/ingress/db/waf/observability
  - "for b in docker docker-compose containerd ctr crictl nerdctl kubectl k3s kubeadm k0s helm kustomize podman runc nginx httpd apache2 haproxy traefik caddy envoy consul-linkerd linkerd cilium calico flannel kube-router modsec coraza openappsec postgres psql mysql mariadbd redis-server redis-cli mongod rabbitmkctl pmosquitto elasticsearch prometheus grafana loki vector fluent-bit fluentd jaeger telegraf node_exporter cadvisor fail2ban-client rkhunter chkrootkit; do p=$(command -v $b 2>/dev/null); [ -n \"$p\" ] && echo \"$b -> $p\"; done"
  - "ss -H -tlnp 2>/dev/null | awk '{print \$4,\$6}' | sort -u"
  - "docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null"
  - "docker images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}' 2>/dev/null | head -40"
  # ── kubernetes / k3s
  - "kubectl get nodes -o wide 2>/dev/null; echo ===NAMESPACES===; kubectl get ns 2>/dev/null"
  - "kubectl get pods -A -o wide 2>/dev/null"
  - "kubectl get svc -A 2>/dev/null"
  - "kubectl get ingress -A 2>/dev/null"
  - "kubectl get deploy,ds,sts -A 2>/dev/null"
  - "kubectl get helmreleases -A 2>/dev/null; helm list -A 2>/dev/null"
  # ── relevant config locations (existence probe, NOT full dump of secrets)
  - "for d in /etc/nginx /etc/traefik /etc/apache2 /etc/httpd /etc/haproxy /etc/kubernetes /etc/rancher /etc/systemd/system /opt /srv /var/www /usr/local/bin /root/.kube; do [ -e \"$d\" ] && echo \"EXISTS $d\"; done"
  - "systemctl list-units --type=service --state=running --no-pager --no-legend 2>/dev/null | awk '{print $1}' | sort -u"
tests: []
evidence_artifacts:
  - "01_os.yml"
  - "02_resources.yml"
  - "03_disks.yml"
  - "04_init.yml"
  - "05_users.yml"
  - "06_passwd.yml"
  - "07_groups.yml"
  - "08_sudo.yml"
  - "09_services_running.yml"
  - "10_services_enabled.yml"
  - "11_timers.yml"
  - "12_sockets.yml"
  - "13_cron.yml"
  - "14_startup.yml"
  - "15_net_ifaces.yml"
  - "16_routes.yml"
  - "17_dns.yml"
  - "18_listening.yml"
  - "19_established.yml"
  - "20_firewall.yml"
  - "21_binaries_detect.yml"
  - "22_listening_proc.yml"
  - "23_docker_ps.yml"
  - "24_docker_images.yml"
  - "25_k8s_nodes.yml"
  - "26_k8s_pods.yml"
  - "27_k8s_svc.yml"
  - "28_k8s_ingress.yml"
  - "29_k8s_workloads.yml"
  - "30_helm.yml"
  - "31_paths.yml"
  - "32_services_sorted.yml"
interpretation: |
  - Build the inventory: every binary that returned a path is a PRESENT technology.
  - listening ports -> map to process -> to a service/container -> to a skill.
  - If `docker`, `kubectl`/`k3s`, an ingress, a DB, a WAF binary exist -> those skills apply.
  - Empty `docker ps` does NOT mean "no docker" — check the binary + the socket + root's docker group.
  - `kubectl get ...` returning empty/Connection refused means "no accessible kubeconfig at runtime", not necessarily "no cluster".
risk_model: discovery produces no findings itself; it seeds skill selection.
remediation_template: |
  n/a — discovery
references:
  - "man systemd, ss, ip, df, lsblk"
---

# System Discovery

This skill is the entry point. Run every `discovery` command via `scripts/ssh_exec.sh`
(read-only, L1). Each command writes one evidence YAML under `evidence/<run-id>/`.
After running, assemble `evidence/<run-id>/inventory.yaml`:

```yaml
host:
os:
kernel:
arch:
init:
cpu:
ram:
disks: [...]
users_high_risk: [...]
services_running: [...]
services_enabled: [...]
cron: [...]
network:
  interfaces: [...]
  routes: [...]
  listening: [{addr, port, proc, pid}]
  established: [...]
firewall: [...]
present_tech: [docker, k3s, ...]
paths_of_interest: [...]
```

Then feed `present_tech` into skill selection. If a present technology has no skill,
generate one (WORKFLOW.md §dynamic skill generation).