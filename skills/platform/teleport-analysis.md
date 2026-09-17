---
id: "teleport_analysis"
name: "Teleport Agent Analysis"
version: "1.0"
category: "teleport"
phase: "diagnose"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "systemd_analysis", "network_analysis"]
provides: ["teleport_version", "teleport_service_state", "teleport_config_validity", "teleport_roles", "teleport_connectivity", "teleport_errors", "teleport_kube_agent_state"]
triggers: ["PRESENT:teleport", "SERVICE:teleport", "SYMPTOM:teleport_agent_failure"]
false_positives:
  - "Un agente puede figurar offline durante una rotacion o reinicio breve; correlacionar estado, logs y conectividad."
  - "Un puerto Teleport no expuesto publicamente puede ser correcto para un agente que solo inicia conexiones salientes."
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/teleport" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Teleport Agent Analysis

## Objetivo
Diagnosticar un agente Teleport sin modificar su estado ni exponer tokens, pines de CA
o material de identidad. Correlaciona proceso, unidad systemd, configuracion estructural,
logs, puertos y conectividad saliente.

## Comandos

### Version, binario y estado de la unidad
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'command -v teleport; teleport version 2>&1; systemctl show teleport.service -p LoadState -p ActiveState -p SubState -p Result -p MainPID -p NRestarts -p ExecMainCode -p ExecMainStatus -p FragmentPath -p ExecStart --no-pager 2>&1; systemctl status teleport.service --no-pager -l 2>&1 | tail -60'
```

### Configuracion estructural y vigencia
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'cfg=$(systemctl show teleport.service -p ExecStart --value 2>/dev/null | grep -oE "(-c|--config(=|[[:space:]]+))[^[:space:] ;]+" | sed -E "s/^(--config=|-c|--config[[:space:]]+)//" | head -1); cfg=${cfg:-/etc/teleport.yaml}; echo "config_path=$cfg"; if [ -r "$cfg" ]; then stat -c "mode=%A owner=%U:%G size=%s mtime=%y" "$cfg"; systemctl show teleport.service -p ActiveEnterTimestamp --no-pager 2>&1; grep -E "^[[:space:]]*(version|nodename|data_dir|auth_server|proxy_server|auth_service|ssh_service|proxy_service|app_service|db_service|kubernetes_service|windows_desktop_service|discovery_service|enabled|listen_addr|public_addr|web_listen_addr|tunnel_listen_addr|join_method|method):" "$cfg" | grep -viE "token:[[:space:]]|ca_pin"; else echo "CONFIG_NOT_READABLE"; fi'
```

### Proceso y sockets
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'pid=$(systemctl show teleport.service -p MainPID --value 2>/dev/null); echo "main_pid=${pid:-0}"; [ "${pid:-0}" -gt 0 ] && ps -p "$pid" -o pid,ppid,user,lstart,etime,%cpu,%mem,args --no-headers 2>&1; echo "=== TELEPORT SOCKETS ==="; ss -lntup 2>/dev/null | grep -E "teleport|:(3022|3023|3024|3025|3080)([[:space:]]|$)" || true; echo "=== TELEPORT CONNECTIONS ==="; ss -tnp 2>/dev/null | grep -E "teleport|:(3023|3024|3025|3080)([[:space:]]|$)" || true'
```

### Errores recientes
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== LAST 200 LINES ==="; journalctl -u teleport.service -n 200 --no-pager -o short-iso 2>&1; echo "=== CURRENT BOOT ERRORS ==="; journalctl -u teleport.service -b -p warning --no-pager -o short-iso 2>&1 | tail -120'
```

### Resolucion y conectividad hacia el proxy configurado
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'cfg=$(systemctl show teleport.service -p ExecStart --value 2>/dev/null | grep -oE "(-c|--config(=|[[:space:]]+))[^[:space:] ;]+" | sed -E "s/^(--config=|-c|--config[[:space:]]+)//" | head -1); cfg=${cfg:-/etc/teleport.yaml}; endpoint=$(grep -E "^[[:space:]]*(proxy_server|auth_server):" "$cfg" 2>/dev/null | head -1 | sed -E "s/^[[:space:]]*[^:]+:[[:space:]]*//; s/[\"'\''\[\],]//g" | awk "{print \$1}"); host=${endpoint%%:*}; port=${endpoint##*:}; [ "$host" = "$port" ] && port=3080; if [ -z "$host" ]; then echo "NO_PROXY_OR_AUTH_ENDPOINT"; exit 0; fi; echo "endpoint_host=$host endpoint_port=$port"; getent ahosts "$host" 2>&1 | head -6; timeout 5 bash -c "</dev/tcp/$host/$port" 2>&1 && echo "tcp_connect=ok" || echo "tcp_connect=failed"'
```

### Agentes Kubernetes
```bash
# [risk:ro] [mode:auto] [requires:kubectl]
ssh {{SSH_TARGET}} 'kubectl get statefulset,daemonset,pod -A -o wide 2>&1 | grep -iE "NAMESPACE|teleport"; kubectl get events -A --sort-by=.lastTimestamp 2>&1 | grep -i teleport | tail -80'
```

```bash
# [risk:ro] [mode:auto] [requires:kubectl,teleport_agent_pod]
ssh {{SSH_TARGET}} 'kubectl describe pod -n <namespace> <teleport-agent-pod> 2>&1; kubectl logs -n <namespace> <teleport-agent-pod> --all-containers=true --since=24h --timestamps=true --tail=800 2>&1'
```

## Analisis / Interpretacion
- `ActiveState=failed` con `ExecMainStatus` no cero confirma fallo local; el journal debe explicar el primer error causal.
- Una configuracion con `mtime` anterior al inicio de un proceso estable fue aceptada por esa version; Teleport 18 no ofrece `teleport config test`.
- Errores `x509`, `bad certificate`, `join`, `token` o `CA pin` indican identidad/registro; no mostrar valores sensibles.
- Errores `no route`, `connection refused`, `timeout` o DNS junto con `tcp_connect=failed` confirman fallo de conectividad.
- `certificate has expired` requiere renovar la identidad del agente siguiendo el metodo de join configurado.
- Un proceso activo y TCP sano no prueban registro; validar en logs la conexion al cluster y ausencia de reintentos.
- Un pod `Running` pero no `Ready`, con timeouts repetidos al `proxy_server`, requiere comparar DNS, ruta y TCP desde el nodo donde fue programado y desde un nodo sano.

## Evidencia producida
- `teleport-service.yml`, `teleport-config.yml`, `teleport-runtime.yml`, `teleport-logs.yml`, `teleport-connectivity.yml`, `teleport-kube-agent.yml`

## Seguridad
Solo lectura. No imprime `token`, `ca_pin`, claves ni contenido de identidades. Toda salida pasa por redaccion.
