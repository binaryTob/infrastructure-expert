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

Retained after passing the creation gate: covers HA state, DCS health and
replication lag beyond the generic PostgreSQL skills, uses stable Patroni
interfaces and is reusable across deployments and audits.

## Objective
Understand the actual state of a Patroni-managed PostgreSQL cluster: node role,
replication, REST API exposure, DCS (etcd) health and recent errors.

## When to use
- `command -v patronictl` succeeds, or `patroni.service` is active.

## Pre-flight (read-only)
```bash
# [risk:info] [mode:auto]
ssh {{SSH_TARGET}} 'command -v patroni patronictl; systemctl is-active patroni'
```

## Commands

### Cluster state (members, role, lag)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'patronictl -c /etc/patroni/config.yml list 2>&1 | head -20'
```

### Configuration (exclude password/token/key secrets)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'grep -vE "^\s*#|password|passwd|secret|token|_key" /etc/patroni/config.yml | head -80'
```

### REST API exposure + auth
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'ss -H -tlnp | grep 8008; grep -A3 -i "restapi" /etc/patroni/config.yml'
```

### DCS health and errors
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'journalctl -u patroni --since "48 hours ago" --no-pager | grep -iE "error|fail|timeout|etcd" | tail -30'
```

### Role/state through psql
```bash
# [risk:ro] [mode:auto] [requires:psql]
ssh {{SSH_TARGET}} 'runuser -u postgres -- psql -X -tAc "SELECT pg_is_in_recovery();"'
ssh {{SSH_TARGET}} 'runuser -u postgres -- psql -X -P pager=off -c "SELECT client_addr,state,sync_state,replay_lag FROM pg_stat_replication;"'
```

## Analysis / interpretation
- All nodes are `Replica` and none is `Leader` -> leaderless cluster (quorum lost).
- Increasing `Lag in MB` -> replica cannot keep up with the leader (I/O or network).
- REST API on `0.0.0.0:8008` without `restapi.authentication` -> unauthenticated cluster control.
- etcd endpoint timeouts -> DCS degradation; fewer than two live members in a
  three-member cluster loses quorum, causing read-only operation / an outage.
- etcd `http` without TLS -> plaintext DCS traffic (potential MITM / control).

## False positives
- `Replica` is the normal role for a standby, not a failure.
- `postgresql@<ver>-main.service` in `failed` state can be expected when Patroni
  manages Postgres directly (Patroni runs pg_ctl; the distribution unit is unused).
- A single etcd endpoint timeout may be transient; correlate more than one sample.

## Thresholds
| Metric | NORMAL | WATCH | WARNING | CRITICAL |
|---------|--------|-------|---------|----------|
| Leader nodes | 1 | 1 | 0 | 0 |
| Replica lag | 0 | < 16MB | < 128MB | > 128MB |
| Live etcd endpoints | 3/3 | 2/3 | 2/3 | 1/3 |
| REST API auth | yes | yes | no | no+0.0.0.0 |

## Evidence produced
- `patroni-cluster.txt`, `patroni-restapi.txt`, `patroni-errors.txt` in `{{OUTPUT_DIR}}`

## Security
Read-only. Never run `patronictl failover/restart/remove` or edit `config.yml` (Level 3).
Redact `config.yml` secrets before storage.
