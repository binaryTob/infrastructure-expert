---
id: "firewall_analysis"
name: "Firewall Analysis"
version: "1.0"
category: "network"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "network_analysis"]
triggers: ["PRESENT:ufw", "PRESENT:iptables", "PRESENT:nftables", "PRESENT:firewalld", "PRESENT:firewall-cmd"]
provides: ["firewall_backend", "firewall_rules", "default_policies", "open_ports_exposed", "logging", "fail2ban_integration"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/firewall" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Firewall Analysis

## Objective
Inventory the active firewall backend (ufw, iptables, nftables, firewalld), enumerate
rules, default policies, exposed ports, logging, and fail2ban integration.
Identifies overly permissive rules, missing egress filtering, and logging gaps.

## Commands

### Backend detection + status
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== BACKEND ==="; command -v ufw >/dev/null && ufw status verbose 2>/dev/null && echo "UFW: active" || echo "UFW: not-installed"; command -v firewall-cmd >/dev/null && firewall-cmd --state 2>/dev/null && echo "firewalld: active" || echo "firewalld: not-installed"; command -v nft >/dev/null && nft list ruleset 2>/dev/null | head -5 && echo "nftables: present" || echo "nftables: not-installed"; iptables -S 2>/dev/null | head -3 && echo "iptables: present"'
```

### UFW detailed rules (if active)
```bash
# [risk:ro] [mode:auto] [requires:ufw]
ssh {{SSH_TARGET}} 'ufw status numbered 2>/dev/null; echo ===; ufw show raw 2>/dev/null | head -80'
```

### iptables / nftables full ruleset
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== IPTABLES -S ==="; iptables -S 2>/dev/null | head -100; echo; echo "=== NFTABLES ==="; nft list ruleset 2>/dev/null | head -120'
```

### firewalld zones + services
```bash
# [risk:ro] [mode:auto] [requires:firewalld]
ssh {{SSH_TARGET}} 'firewall-cmd --list-all-zones 2>/dev/null; echo ===; firewall-cmd --get-active-zones 2>/dev/null'
```

### Default policies (critical)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== DEFAULT POLICIES ==="; iptables -L -n 2>/dev/null | grep -E "^Chain|policy" | head -20; nft list ruleset 2>/dev/null | grep -i "policy" | head -10'
```

### Exposed ports vs firewall rules
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== LISTENING PORTS ==="; ss -H -tlnp 2>/dev/null; echo; echo "=== UFW ALLOWED ==="; ufw status 2>/dev/null | grep -E "^[0-9]+" || echo "ufw not active"; echo "=== IPTABLES INPUT ACCEPT ==="; iptables -L INPUT -n 2>/dev/null | grep -E "ACCEPT|DROP|REJECT" | head -30'
```

### Logging rules
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== LOG RULES ==="; iptables -L -n 2>/dev/null | grep -i log; nft list ruleset 2>/dev/null | grep -i log'
```

### fail2ban integration (if present)
```bash
# [risk:ro] [mode:auto] [requires:fail2ban]
ssh {{SSH_TARGET}} 'fail2ban-client status 2>/dev/null; echo ===; for jail in $(fail2ban-client status 2>/dev/null | grep "Jail list" | cut -d: -f2 | tr "," "\n"); do echo "=== $jail ==="; fail2ban-client status "$jail" 2>/dev/null; done'
```

## Analysis

- **No firewall active** (`ufw inactive`, `firewalld not running`, `iptables default ACCEPT`): all ports exposed to the network boundary — HIGH if public IP.
- **Default INPUT = ACCEPT**: no implicit deny; every listening port is exposed unless explicitly blocked.
- **SSH (22) open to 0.0.0.0/0** without fail2ban / rate limiting: HIGH brute-force risk.
- **Egress not filtered**: compromised container can reach internet freely (C2, data exfil).
- **No LOG rules**: silent drops/accepts; no visibility into attacks or misconfigs.
- **fail2ban absent or no jails**: SSH brute-force unmitigated.
- **Docker `iptables` chains present** (`DOCKER-USER`, `DOCKER`): Docker manages its own rules; verify `DOCKER-USER` isn't blank (allows pre-DOCKER rules).

## Thresholds

| Metric | NORMAL | WATCH | WARNING | CRITICAL |
|--------|--------|-------|---------|----------|
| Default INPUT policy | DROP | DROP | ACCEPT (non-public) | ACCEPT (public) |
| SSH open to world | no | no | yes (with fail2ban) | yes (no fail2ban) |
| Logging rules present | yes | yes | no | no |
| fail2ban active with sshd jail | yes | yes | no | no |

## False Positives
- Cloud provider security groups / SG rules are NOT visible locally; a host may appear "open" locally but be protected at the network edge. Correlate with cloud SG before flagging CRITICAL.
- `DOCKER` chain rules are managed by Docker; don't flag as "manual changes needed" unless `DOCKER-USER` is missing.

## Evidence
- `backend.txt`, `ufw-rules.txt`, `iptables.txt`, `nftables.txt`, `firewalld-zones.txt`, `default-policies.txt`, `exposed-ports.txt`, `logging.txt`, `fail2ban.txt`

## Security
Read-only. Never `ufw enable/disable`, `iptables -A/-D`, `firewall-cmd --add/--remove`, or modify fail2ban jails (Level 3).