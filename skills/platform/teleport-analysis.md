---
id: "teleport_analysis"
name: "Teleport Agent Analysis"
version: "1.0"
category: "teleport"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "systemd_analysis", "network_analysis"]
provides: ["teleport_version", "teleport_service_state", "teleport_config_validity", "teleport_roles", "teleport_connectivity", "teleport_errors", "teleport_kube_agent_state"]
triggers: ["PRESENT:teleport", "SERVICE:teleport", "SYMPTOM:teleport_agent_failure"]
false_positives:
  - "An agent may appear offline during rotation or a brief restart; correlate state, logs and connectivity."
  - "A Teleport port without public exposure may be correct for an agent that only initiates outbound connections."
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/teleport" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Teleport Agent Analysis

## Objective
Diagnose a Teleport agent without modifying state or exposing tokens, CA pins or
identity material. Correlate its process, systemd unit, structural configuration,
logs, ports and outbound connectivity.

## Commands

### Version, binary and unit state
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'command -v teleport; teleport version 2>&1; systemctl show teleport.service -p LoadState -p ActiveState -p SubState -p Result -p MainPID -p NRestarts -p ExecMainCode -p ExecMainStatus -p FragmentPath -p ExecStart --no-pager 2>&1; systemctl status teleport.service --no-pager -l 2>&1 | tail -60'
```

### Structural configuration and timestamps
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'cfg=$(systemctl show teleport.service -p ExecStart --value 2>/dev/null | grep -oE "(-c|--config(=|[[:space:]]+))[^[:space:] ;]+" | sed -E "s/^(--config=|-c|--config[[:space:]]+)//" | head -1); cfg=${cfg:-/etc/teleport.yaml}; echo "config_path=$cfg"; if [ -r "$cfg" ]; then stat -c "mode=%A owner=%U:%G size=%s mtime=%y" "$cfg"; systemctl show teleport.service -p ActiveEnterTimestamp --no-pager 2>&1; grep -E "^[[:space:]]*(version|nodename|data_dir|auth_server|proxy_server|auth_service|ssh_service|proxy_service|app_service|db_service|kubernetes_service|windows_desktop_service|discovery_service|enabled|listen_addr|public_addr|web_listen_addr|tunnel_listen_addr|join_method|method):" "$cfg" | grep -viE "token:[[:space:]]|ca_pin"; else echo "CONFIG_NOT_READABLE"; fi'
```

### Process and sockets
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'pid=$(systemctl show teleport.service -p MainPID --value 2>/dev/null); echo "main_pid=${pid:-0}"; [ "${pid:-0}" -gt 0 ] && ps -p "$pid" -o pid,ppid,user,lstart,etime,%cpu,%mem,args --no-headers 2>&1; echo "=== TELEPORT SOCKETS ==="; ss -lntup 2>/dev/null | grep -E "teleport|:(3022|3023|3024|3025|3080)([[:space:]]|$)" || true; echo "=== TELEPORT CONNECTIONS ==="; ss -tnp 2>/dev/null | grep -E "teleport|:(3023|3024|3025|3080)([[:space:]]|$)" || true'
```

### Recent errors
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== LAST 200 LINES ==="; journalctl -u teleport.service -n 200 --no-pager -o short-iso 2>&1; echo "=== CURRENT BOOT ERRORS ==="; journalctl -u teleport.service -b -p warning --no-pager -o short-iso 2>&1 | tail -120'
```

### Resolution and connectivity to the configured proxy
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'cfg=$(systemctl show teleport.service -p ExecStart --value 2>/dev/null | grep -oE "(-c|--config(=|[[:space:]]+))[^[:space:] ;]+" | sed -E "s/^(--config=|-c|--config[[:space:]]+)//" | head -1); cfg=${cfg:-/etc/teleport.yaml}; endpoint=$(grep -E "^[[:space:]]*(proxy_server|auth_server):" "$cfg" 2>/dev/null | head -1 | sed -E "s/^[[:space:]]*[^:]+:[[:space:]]*//; s/[\"'\''\[\],]//g" | awk "{print \$1}"); host=${endpoint%%:*}; port=${endpoint##*:}; [ "$host" = "$port" ] && port=3080; if [ -z "$host" ]; then echo "NO_PROXY_OR_AUTH_ENDPOINT"; exit 0; fi; echo "endpoint_host=$host endpoint_port=$port"; getent ahosts "$host" 2>&1 | head -6; timeout 5 bash -c "</dev/tcp/$host/$port" 2>&1 && echo "tcp_connect=ok" || echo "tcp_connect=failed"'
```

### Kubernetes agents
```bash
# [risk:ro] [mode:auto] [requires:kubectl]
ssh {{SSH_TARGET}} 'kubectl get statefulset,daemonset,pod -A -o wide 2>&1 | grep -iE "NAMESPACE|teleport"; kubectl get events -A --sort-by=.lastTimestamp 2>&1 | grep -i teleport | tail -80'
```

```bash
# [risk:ro] [mode:auto] [requires:kubectl,teleport_agent_pod]
ssh {{SSH_TARGET}} 'kubectl describe pod -n <namespace> <teleport-agent-pod> 2>&1; kubectl logs -n <namespace> <teleport-agent-pod> --all-containers=true --since=24h --timestamps=true --tail=800 2>&1'
```

## Analysis / interpretation
- `ActiveState=failed` with nonzero `ExecMainStatus` confirms a local failure; use the journal to identify the first causal error.
- Configuration whose `mtime` predates a stable process startup was accepted by that version; Teleport 18 does not provide `teleport config test`.
- `x509`, `bad certificate`, `join`, `token` or `CA pin` errors indicate identity/registration issues; never display sensitive values.
- `no route`, `connection refused`, `timeout` or DNS errors combined with `tcp_connect=failed` confirm connectivity failure.
- `certificate has expired` requires agent identity renewal using the configured join method.
- An active process and healthy TCP do not prove registration; verify cluster connectivity and absence of retries in logs.
- For a `Running` but not `Ready` pod with repeated `proxy_server` timeouts, compare DNS, routes and TCP from its scheduled node and a healthy node.

## Evidence produced
- `teleport-service.yml`, `teleport-config.yml`, `teleport-runtime.yml`, `teleport-logs.yml`, `teleport-connectivity.yml`, `teleport-kube-agent.yml`

## Security
Read-only. Do not print `token`, `ca_pin`, keys or identity contents. Redact all output.
