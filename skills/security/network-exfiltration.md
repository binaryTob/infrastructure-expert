---
id: "network_exfiltration"
name: "Network Exfiltration Detection"
version: "1.0"
category: "security"
phase: "forensic"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "network_analysis"]
triggers: []
provides: ["outbound_connections", "suspicious_processes", "cron_network_usage"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/network-exfiltration" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Network Exfiltration Detection

## Objective
Detect evidence of data exfiltration through network channels: suspicious outbound
connections, curl/wget usage in cron, SSH tunnels, DNS exfiltration, and
processes with network access that shouldn't have it.

## Commands

### 1. Established outbound connections
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== ESTABLISHED OUTBOUND CONNECTIONS ==="; ss -tnp state established | grep -vE "127\.0\.0\.1|::1|\[::1\]" | awk "{print \$5,\$6}" | sort -u; echo; echo "=== CONNECTIONS WITH PROCESS INFO ==="; ss -tnp state established | grep -vE "127\.0\.0\.1|::1"'
```

### 2. Processes with network access (curl, wget, nc, ssh)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== PROCESSES WITH NETWORK TOOLS ==="; ps aux | grep -iE "curl|wget|nc |ncat|socat|ssh.*-[LR]|rsync.*@|scp " | grep -v grep; echo; echo "=== PROCESSES LISTENING ==="; ss -tlnp | awk "{print \$6}" | grep -oP "\"\K[^\"]+" | sort -u'
```

### 3. Cron jobs with network commands
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== CRON JOBS WITH NETWORK COMMANDS ==="; for f in /etc/crontab /etc/cron.d/* /var/spool/cron/crontabs/*; do
  [ -f "$f" ] || continue
  echo "--- $f ---"
  grep -nE "curl|wget|nc |ncat|ssh|scp|rsync|python.*urllib|ruby.*net/http|perl.*LWP" "$f" 2>/dev/null
done; echo; echo "=== SYSTEMD TIMERS WITH NETWORK ==="; systemctl list-timers --all 2>/dev/null | head -20'
```

### 4. SSH tunnels and port forwarding
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== SSH PROCESSES WITH TUNNELS ==="; ps aux | grep ssh | grep -v grep | grep -E "\-[LRD]"; echo; echo "=== SSH CONNECTIONS ==="; ss -tnp | grep ssh | grep -v "LISTEN"'
```

### 5. DNS queries (suspicious patterns)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== RECENT DNS QUERIES (if logged) ==="; journalctl --since "7 days ago" 2>/dev/null | grep -iE "query.*AAAA|query.*TXT|query.*MX|query.*CNAME" | grep -vE "google|cloudflare|github|letsencrypt|amazonaws|akamai|microsoft|facebook" | tail -20; echo; echo "=== RESOLV.CONF ==="; cat /etc/resolv.conf 2>/dev/null'
```

### 6. Processes with redirected I/O (data channels)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== PROCESSES WITH PIPE/SOCKET FILE DESCRIPTORS ==="; for pid in $(ls /proc 2>/dev/null | grep "^[0-9]" | head -300); do
  if [ -d "/proc/$pid/fd" ] 2>/dev/null; then
    pipe_count=$(ls -la /proc/$pid/fd 2>/dev/null | grep -c "pipe:")
    socket_count=$(ls -la /proc/$pid/fd 2>/dev/null | grep -c "socket:")
    if [ "$socket_count" -gt 2 ]; then
      comm=$(cat /proc/$pid/comm 2>/dev/null)
      echo "PID $pid ($comm) - sockets: $socket_count, pipes: $pipe_count"
    fi
  fi
done 2>/dev/null | head -20'
```

### 7. Sniffers/packet capture tools
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== PACKET CAPTURE PROCESSES ==="; ps aux | grep -iE "tcpdump|tshark|wireshark|ngrep|dnstop|iftop|nethogs" | grep -v grep; echo; echo "=== PCAP FILES ==="; find / -name "*.pcap" -o -name "*.pcapng" -o -name "*.cap" 2>/dev/null | head -10; echo; echo "=== PROMISCUOUS MODE ==="; ip link show 2>/dev/null | grep -i "promisc"'
```

### 8. Network-related cron at unusual hours
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== CRON SCHEDULES ==="; for f in /etc/crontab /etc/cron.d/* /var/spool/cron/crontabs/*; do
  [ -f "$f" ] || continue
  echo "--- $f ---"
  cat "$f" 2>/dev/null | grep -v "^#" | grep -v "^$"
done'
```

### 9. Outbound connections to non-standard ports
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== OUTBOUND TO NON-STANDARD PORTS ==="; ss -tnp state established | grep -vE "127\.0\.0\.1|::1" | awk "{print \$5}" | grep -oP ":\K[0-9]+" | sort -n | uniq -c | sort -rn | head -20; echo; echo "=== CONNECTION DESTINATIONS ==="; ss -tnp state established | grep -vE "127\.0\.0\.1|::1" | awk "{print \$5}" | sort -u | head -30'
```

### 10. Webhook/notification scripts in cron
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== WEBHOOK/NOTIFICATION SCRIPTS ==="; grep -rlE "webhook|slack|telegram|discord|pagerduty|mail -s|sendmail|mutt" /etc/cron* /var/spool/cron/ /etc/cron.d/ 2>/dev/null; echo; echo "=== SCRIPTS WITH CURL POST ==="; grep -rlE "curl.*-X POST|curl.*--data|wget.*--post" /etc/cron* /var/spool/cron/ /usr/local/bin/ /opt/scripts/ 2>/dev/null | head -10'
```

## Analysis

### Severity mapping
| Finding | Severity | Confidence |
|---------|----------|------------|
| curl/wget in cron to unknown endpoint | HIGH | MEDIUM |
| SSH tunnel (-R/-L/-D) active | MEDIUM | HIGH |
| tcpdump/tshark running | HIGH | HIGH |
| Outbound to port 4444/1337/31337 | HIGH | MEDIUM |
| Cron job running at 2-5 AM with curl | MEDIUM | MEDIUM |
| Process with many sockets (data channel) | MEDIUM | LOW |
| DNS queries to unusual domains | MEDIUM | MEDIUM |
| Promiscuous mode on network interface | HIGH | HIGH |
| Webhook to Slack/Discord with data payload | MEDIUM | MEDIUM |
| Outbound connection to residential IP | MEDIUM | LOW |

### Correlation
- Cross-reference with `filesystem_forensics` for bash_history with curl/wget commands
- Cross-reference with `audit_logs_forensics` for network-related audit events
- Cross-reference with `credential_exposure_analysis` for what data might have been exfiltrated

## Evidence
- `outbound-connections.yml` — established outbound connections
- `suspicious-processes.yml` — processes with network tools
- `cron-network-usage.yml` — cron jobs with network commands
- `ssh-tunnels.yml` — SSH tunnel/port forwarding activity
- `dns-queries.yml` — suspicious DNS queries

## False Positives
- Legitimate monitoring agents (Prometheus, Datadog) making outbound connections
- Package managers (apt, yum) downloading updates
- NTP synchronization
- Backup scripts uploading to known cloud storage (S3, GCS)
- Webhook notifications for deployment alerts (check if it's a known Slack/Discord webhook)

## Security
Read-only. Never output actual connection payloads or DNS query contents.
Only report: source PID, destination IP:port, protocol, process name.
All output must pass through `scripts/redact.sh`.
