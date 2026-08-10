---
id: "network_analysis"
name: "Network Analysis"
version: "2.0"
category: "network"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory"]
provides: ["interfaces", "routes", "open_ports", "port_process_map", "connections"]
triggers: []
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/network" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Network Analysis

Map host + cluster network: interfaces, routes, listening ports, firewall, edge ingress
exposure, port->process->service->container links, CNI.

system_inventory already ran `ip -br addr` and `ip route | head -5` for triage.
This skill does the FULL network analysis. If kubectl is present, it CONSUMES
`kubectl get svc -A` and `kubectl get networkpolicy -A` evidence from `kubernetes_analysis`
rather than re-fetching.

## Commands

### Interfaces (full — system_inventory only did `ip -br addr`)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ip -br addr 2>/dev/null; echo ===; ip -o addr 2>/dev/null; echo ===; ip link show 2>/dev/null'
```

### Routes (full — system_inventory only did `ip route | head -5`)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ip route 2>/dev/null; echo ===; ip -6 route 2>/dev/null | head -20'
```

### DNS
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'cat /etc/resolv.conf 2>/dev/null; echo ===; cat /etc/hosts 2>/dev/null; echo ===; systemd-resolve --status 2>/dev/null | head -30 || resolvectl status 2>/dev/null | head -30'
```

### Listening ports (full — system_inventory only did a one-liner)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== TCP ==="; ss -H -tlnp 2>/dev/null; echo; echo "=== UDP ==="; ss -H -ulnp 2>/dev/null'
```

### Established connections
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ss -H -tnp state established 2>/dev/null | head -60'
```

### Firewall
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== UFW ==="; command -v ufw >/dev/null && ufw status verbose 2>/dev/null || echo "ufw no presente"; echo; echo "=== IPTABLES ==="; iptables -S 2>/dev/null | head -60; echo; echo "=== NFT ==="; nft list ruleset 2>/dev/null | head -80'
```

### Connection count summary
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ss -s 2>/dev/null; echo; ss -tna 2>/dev/null | awk '"'"'{print $4}'"'"' | awk -F: '"'"'{print $NF}'"'"' | sort | uniq -c | sort -rn | head -15'
```

### Kubernetes networking (hostNetwork pods only — svc/netpol consumed from kubernetes_analysis)
```bash
# [risk:ro] [mode:auto] [requires:kubectl]
ssh {{SSH_TARGET}} 'kubectl get pods -A -o jsonpath='"'"'{range .items[*]}{.metadata.name} hostNetwork={.spec.hostNetwork}{"\\n"}{end}'"'"' 2>/dev/null | grep "true"'
```

### Edge curl (verify from host)
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'for host in localhost $(hostname -I 2>/dev/null); do curl -skI --connect-timeout 5 https://$host/ 2>/dev/null | head -3; done'
```

## Analysis
- Map each listening socket: addr:port -> PID -> process -> container/pod/service.
- 0.0.0.0 binding = external; 127.0.0.1 = local only.
- No host firewall (ufw disabled, iptables default) = rely on cloud security-group + k8s.
- `hostNetwork: true` pods = shared host network namespace (no isolation).
- Read `kubernetes/netpol.txt` from kubernetes_analysis for NetworkPolicy evidence.
- Read `kubernetes/svc.txt` from kubernetes_analysis for service inventory.
- No NetworkPolicy = full east-west pod reachability.

## Evidence
- `interfaces.txt`, `routes.txt`, `dns.txt`, `listening.txt`, `established.txt`, `firewall.txt`, `conn-count.txt`, `k8s-hostnet.txt`, `edge-curl.txt`

## Security
Read-only. Report exposure, never modify firewall rules.