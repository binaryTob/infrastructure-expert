---
id: "etcd_analysis"
name: "etcd Cluster Analysis"
version: "1.0"
category: "etcd"
phase: "diagnose"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "network_analysis"]
provides: ["etcd_version", "etcd_members", "etcd_endpoints", "etcd_quorum", "etcd_alarms", "etcd_latency"]
triggers: ["PRESENT:etcd", "PRESENT:etcdctl", "SERVICE:etcd"]
false_positives:
  - "Un endpoint remoto inaccesible desde redes ajenas puede estar protegido correctamente; probar desde un miembro del cluster."
  - "Un cambio de lider aislado no implica degradacion; correlacionar con timeouts y una serie temporal."
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/etcd" }
  SSH_TARGET: { type: "string", required: true }
  SAMPLE_INTERVAL: { type: "duration", default: "10s", required: false }
  SAMPLE_COUNT: { type: "integer", default: 4, required: false }
output: { format: "json", schema: "output_schema" }
---

# etcd Cluster Analysis

## Objetivo
Verificar membresia, quorum, lider, salud, latencia, alarmas y exposicion de un cluster
etcd independiente sin leer claves ni modificar estado.

## Comandos

### Version y configuracion efectiva
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'command -v etcd; command -v etcdctl; etcd --version 2>/dev/null | head -5; etcdctl version 2>/dev/null; systemctl show etcd.service -p FragmentPath -p ExecStart -p EnvironmentFiles -p ActiveState -p NRestarts 2>/dev/null'
```

### Miembros y estado de endpoints
```bash
# [risk:ro] [mode:auto] [requires:etcdctl]
ssh {{SSH_TARGET}} 'ETCDCTL_API=3 etcdctl --endpoints=http://127.0.0.1:2379 member list -w table 2>&1; echo ===STATUS===; ETCDCTL_API=3 etcdctl --endpoints=http://127.0.0.1:2379 endpoint status -w table 2>&1; echo ===ALARMS===; ETCDCTL_API=3 etcdctl --endpoints=http://127.0.0.1:2379 alarm list 2>&1'
```

### Autenticacion y transporte (compatible con etcd 3.4)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo ===AUTH===; curl -fsS --connect-timeout 2 --max-time 5 http://127.0.0.1:2379/v2/auth/enable 2>&1; echo; echo ===TRANSPORT===; tr "\0" "\n" </proc/$(pidof etcd)/environ 2>/dev/null | grep -E "^ETCD_(LISTEN|ADVERTISE|CLIENT_CERT_AUTH|PEER_CLIENT_CERT_AUTH|TRUSTED_CA_FILE|CERT_FILE|KEY_FILE)="'
```

### Salud y latencia en serie
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'for i in 1 2 3 4; do date -u +%FT%TZ; curl -fsS --connect-timeout 2 --max-time 5 -w " code=%{http_code} connect=%{time_connect} total=%{time_total}\n" http://127.0.0.1:2379/health 2>&1; sleep 10; done'
```

### Metricas operativas seleccionadas
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'curl -fsS --connect-timeout 2 --max-time 5 http://127.0.0.1:2379/metrics 2>/dev/null | grep -E "^(etcd_server_has_leader|etcd_server_leader_changes_seen_total|etcd_server_proposals_(failed|pending)_total|etcd_server_slow_apply_total|etcd_disk_backend_commit_duration_seconds|etcd_disk_wal_fsync_duration_seconds|etcd_mvcc_db_total_size_in_bytes|process_resident_memory_bytes)"'
```

### Errores y elecciones recientes
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'journalctl -u etcd.service --since "24 hours ago" --no-pager 2>/dev/null | grep -iE "leader|election|timeout|unhealthy|unreachable|failed|slow|took too long|alarm|corrupt|space" | tail -120'
```

## Analisis / Interpretacion
- `isLeader=true` exactamente una vez y todos los miembros `started`: quorum observable.
- `endpoint health` fallando o `/health` alternando: degradacion confirmada, no un evento aislado.
- Timeouts junto con `leader_changes` creciente: investigar perdida/latencia de red entre peers.
- `proposals_pending > 0`, `proposals_failed` creciente o fsync p99 alto: correlacionar con I/O.
- Cliente o peer en IP publica sin TLS requiere firewall restrictivo; validar reglas antes de reportar exposicion.
- En los histogramas acumulativos, restar cada bucket del `count` permite cuantificar
  fsyncs por encima del umbral (por ejemplo, `count - le=1.024` = operaciones >1.024 s).
- La skill nunca ejecuta `put`, `del`, `compact`, `defrag`, `snapshot restore` ni cambios de membresia.

## Umbrales
| Metrica | NORMAL | WARNING | CRITICAL |
|---------|--------|---------|----------|
| miembros sanos | todos | uno intermitente con quorum | sin quorum |
| `/health` | 4/4 sanos | 1/4 fallos | >=2/4 fallos |
| propuestas pendientes | 0 | >0 transitorio | >0 sostenido |

## Evidencia producida
- `version.yml`, `members.yml`, `auth-transport.yml`, `health-series.yml`, `metrics.yml`, `errors.yml`

## Seguridad
Solo metadata y salud. No se enumeran claves ni valores. Toda salida pasa por redaccion.
