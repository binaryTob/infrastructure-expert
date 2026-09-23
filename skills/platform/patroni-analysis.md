---
id: "patroni_analysis"
name: "Patroni PostgreSQL HA Analysis"
version: "1.0"
category: "patroni"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "systemd_analysis", "network_analysis", "database_analysis"]
triggers: ["PRESENT:patroni", "SERVICE:patroni", "PRESENT:patronictl"]
provides: ["patroni_cluster_state", "patroni_restapi_exposure", "patroni_dcs_endpoints", "patroni_dcs_health", "pg_role", "pg_replication_lag"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/patroni" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Patroni PostgreSQL HA Analysis

Capacidad conservada tras superar el gate de creacion: cubre estado HA, DCS y lag de
replicacion que no ofrecen las skills genericas de PostgreSQL, usa interfaces estables
de Patroni y es reutilizable entre despliegues y auditorias.

## Objetivo
Entender el estado real del cluster PostgreSQL gestionado por Patroni: rol del nodo,
replicacion, exposicion de la REST API, salud del DCS (etcd) y errores recientes.

## Cuando usarla
- `command -v patronictl` presente, o unit `patroni.service` activa.

## Pre-flight (read-only)
```bash
# [risk:info] [mode:auto]
ssh {{SSH_TARGET}} 'command -v patroni patronictl; systemctl is-active patroni'
```

## Comandos

### Estado del cluster (miembros, rol, lag)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'patronictl -c /etc/patroni/config.yml list 2>&1 | head -20'
```

### Configuracion (sin secretos: excluye password/token/key)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'grep -vE "^\s*#|password|passwd|secret|token|_key" /etc/patroni/config.yml | head -80'
```

### REST API exposure + auth
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ss -H -tlnp | grep 8008; grep -A3 -i "restapi" /etc/patroni/config.yml'
```

### DCS health + errores
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'journalctl -u patroni --since "48 hours ago" --no-pager | grep -iE "error|fail|timeout|etcd" | tail -30'
```

### Rol/estado desde psql
```bash
# [risk:ro] [mode:auto] [requires:psql]
ssh {{SSH_TARGET}} 'runuser -u postgres -- psql -X -tAc "SELECT pg_is_in_recovery();"'
ssh {{SSH_TARGET}} 'runuser -u postgres -- psql -X -P pager=off -c "SELECT client_addr,state,sync_state,replay_lag FROM pg_stat_replication;"'
```

## Analisis / Interpretacion
- Todos los nodos `Replica` y ninguno `Leader` -> cluster sin lider (quorum perdido).
- `Lag in MB` creciente -> replica no alcanza al leader (I/O o red).
- REST API en `0.0.0.0:8008` sin `restapi.authentication` -> control del cluster sin auth.
- Endpoints etcd con timeouts -> degradacion del DCS; con <2 vivos se pierde quorum y
  el cluster pasa a solo lectura / cae.
- Protocolo etcd `http` sin TLS -> DCS en texto claro (posible MITM / control).

## Falsos positivos
- Nodos `Replica` es lo normal en un standby; no es un fallo.
- `postgresql@<ver>-main.service` en `failed` es EXPECTED cuando Patroni gestiona
  Postgres directamente (Patroni hace su propio pg_ctl; la unit de distro no se usa).
- Timeout a un endpoint etcd aislado puede ser transitorio; correlacionar con >1 muestra.

## Umbrales
| Metrica | NORMAL | WATCH | WARNING | CRITICAL |
|---------|--------|-------|---------|----------|
| Nodos con Leader | 1 | 1 | 0 | 0 |
| Lag replica | 0 | < 16MB | < 128MB | > 128MB |
| etcd endpoints vivos | 3/3 | 2/3 | 2/3 | 1/3 |
| REST API auth | yes | yes | no | no+0.0.0.0 |

## Evidencia producida
- `patroni-cluster.txt`, `patroni-restapi.txt`, `patroni-errors.txt` en `{{OUTPUT_DIR}}`

## Seguridad
Read-only. Nunca `patronictl failover/restart/remove`, ni editar `config.yml` (Level 3).
Redactar secretos de `config.yml` antes de almacenar.
