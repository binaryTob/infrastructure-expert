---
id: "etcd_analysis"
name: "etcd Cluster Analysis"
version: "1.0"
category: "etcd"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "network_analysis"]
provides: ["etcd_version", "etcd_members", "etcd_endpoints", "etcd_quorum", "etcd_alarms", "etcd_latency"]
triggers: ["PRESENT:etcd", "PRESENT:etcdctl", "SERVICE:etcd"]
false_positives:
  - "A remote endpoint unreachable from external networks may be correctly protected; test from a cluster member."
  - "A single leader change does not imply degradation; correlate with timeouts and a time series."
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/etcd" }
  SSH_TARGET: { type: "string", required: true }
  SAMPLE_INTERVAL: { type: "duration", default: "10s", required: false }
  SAMPLE_COUNT: { type: "integer", default: 4, required: false }
output: { format: "json", schema: "output_schema" }
---

# etcd Cluster Analysis

## Objective
Check membership, quorum, leader, health, latency, alarms and exposure of a
standalone etcd cluster without reading keys or modifying state.

## Commands

### Version and effective configuration
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'command -v etcd; command -v etcdctl; etcd --version 2>/dev/null | head -5; etcdctl version 2>/dev/null; systemctl show etcd.service -p FragmentPath -p ExecStart -p EnvironmentFiles -p ActiveState -p NRestarts 2>/dev/null'
```

### Members and endpoint status
```bash
# [risk:ro] [mode:auto] [requires:etcdctl]
ssh {{SSH_TARGET}} 'ETCDCTL_API=3 etcdctl --endpoints=http://127.0.0.1:2379 member list -w table 2>&1; echo ===STATUS===; ETCDCTL_API=3 etcdctl --endpoints=http://127.0.0.1:2379 endpoint status -w table 2>&1; echo ===ALARMS===; ETCDCTL_API=3 etcdctl --endpoints=http://127.0.0.1:2379 alarm list 2>&1'
```

### Authentication and transport (compatible with etcd 3.4)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo ===AUTH===; curl -fsS --connect-timeout 2 --max-time 5 http://127.0.0.1:2379/v2/auth/enable 2>&1; echo; echo ===TRANSPORT===; tr "\0" "\n" </proc/$(pidof etcd)/environ 2>/dev/null | grep -E "^ETCD_(LISTEN|ADVERTISE|CLIENT_CERT_AUTH|PEER_CLIENT_CERT_AUTH|TRUSTED_CA_FILE|CERT_FILE|KEY_FILE)="'
```

### Health and latency time series
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'for i in 1 2 3 4; do date -u +%FT%TZ; curl -fsS --connect-timeout 2 --max-time 5 -w " code=%{http_code} connect=%{time_connect} total=%{time_total}\n" http://127.0.0.1:2379/health 2>&1; sleep 10; done'
```

### Selected operational metrics
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'curl -fsS --connect-timeout 2 --max-time 5 http://127.0.0.1:2379/metrics 2>/dev/null | grep -E "^(etcd_server_has_leader|etcd_server_leader_changes_seen_total|etcd_server_proposals_(failed|pending)_total|etcd_server_slow_apply_total|etcd_disk_backend_commit_duration_seconds|etcd_disk_wal_fsync_duration_seconds|etcd_mvcc_db_total_size_in_bytes|process_resident_memory_bytes)"'
```

### Recent errors and elections
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'journalctl -u etcd.service --since "24 hours ago" --no-pager 2>/dev/null | grep -iE "leader|election|timeout|unhealthy|unreachable|failed|slow|took too long|alarm|corrupt|space" | tail -120'
```

## Analysis / interpretation
- Exactly one `isLeader=true` and all members `started`: observable quorum.
- Failing `endpoint health` or fluctuating `/health`: confirmed degradation rather than a single event.
- Timeouts with increasing `leader_changes`: investigate peer network loss/latency.
- `proposals_pending > 0`, increasing `proposals_failed` or high fsync p99: correlate with I/O.
- A public client/peer IP without TLS needs restrictive firewall rules; validate them before reporting exposure.
- In cumulative histograms, subtract each bucket from `count` to quantify fsyncs
  above a threshold (e.g. `count - le=1.024` = operations taking >1.024 s).
- Never execute `put`, `del`, `compact`, `defrag`, `snapshot restore` or membership changes.

## Thresholds
| Metric | NORMAL | WARNING | CRITICAL |
|---------|--------|---------|----------|
| Healthy members | all | one intermittent member, quorum retained | no quorum |
| `/health` | 4/4 healthy | 1/4 failures | >=2/4 failures |
| Pending proposals | 0 | transient >0 | sustained >0 |

## Evidence produced
- `version.yml`, `members.yml`, `auth-transport.yml`, `health-series.yml`, `metrics.yml`, `errors.yml`

## Security
Metadata and health only. Do not enumerate keys or values. Redact all output.
