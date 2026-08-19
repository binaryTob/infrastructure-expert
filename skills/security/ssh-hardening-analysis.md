---
id: "ssh_hardening_analysis"
name: "SSH Hardening & fail2ban Analysis"
version: "1.0"
category: "security"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "systemd_analysis", "network_analysis"]
triggers: ["PRESENT:fail2ban", "PRESENT:ssh"]
provides: ["sshd_config", "fail2ban_jails", "ban_stats", "ssh_auth", "authorized_keys", "ssh_exposure", "hostkeys"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/ssh-hardening" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# SSH Hardening & fail2ban Analysis

## Objective
Comprehensive SSH daemon configuration audit + fail2ban jail inventory. Detects
weak configurations (root login, password auth, weak ciphers/MACs), fail2ban
gaps (missing jails, high ban thresholds), and brute-force evidence in logs.

## Commands

### sshd_config deep audit
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== SSHD CONFIG ==="; grep -vE "^#|^$" /etc/ssh/sshd_config | sort; echo; echo "=== KEY SETTINGS ==="; for k in PermitRootLogin PasswordAuthentication PubkeyAuthentication PermitEmptyPasswords MaxAuthTries ClientAliveInterval ClientAliveCountMax LoginGraceTime MaxSessions AllowUsers AllowGroups DenyUsers DenyGroups Ciphers MACs KexAlgorithms HostKeyAlgorithms; do grep -i "^$k" /etc/ssh/sshd_config 2>/dev/null || echo "$k: (default)"; done'
```

### Host keys inventory
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== HOST KEYS ==="; for f in /etc/ssh/ssh_host_*_key.pub; do [ -f "$f" ] && ssh-keygen -lf "$f" 2>/dev/null; done'
```

### fail2ban status + all jails (if present)
```bash
# [risk:ro] [mode:auto] [requires:fail2ban]
ssh {{SSH_TARGET}} 'echo "=== FAIL2BAN STATUS ==="; fail2ban-client status 2>/dev/null; echo; for jail in $(fail2ban-client status 2>/dev/null | grep "Jail list" | cut -d: -f2 | tr "," "\n" | sed "s/ //g"); do [ -n "$jail" ] && echo "=== JAIL: $jail ===" && fail2ban-client status "$jail" 2>/dev/null; done'
```

### fail2ban config (jail.local / jail.d)
```bash
# [risk:ro] [mode:auto] [requires:fail2ban]
ssh {{SSH_TARGET}} 'echo "=== JAIL.CONF/LOCAL ==="; cat /etc/fail2ban/jail.local 2>/dev/null || cat /etc/fail2ban/jail.conf 2>/dev/null | head -80; echo; echo "=== JAIL.D ==="; ls -la /etc/fail2ban/jail.d/ 2>/dev/null; cat /etc/fail2ban/jail.d/*.conf 2>/dev/null'
```

### SSH auth log analysis (recent failures)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== RECENT FAILURES ==="; journalctl -u ssh --since "24 hours ago" 2>/dev/null | grep -iE "failed|invalid|error" | head -30; echo; echo "=== TOP ATTACKERS ==="; journalctl -u ssh --since "7 days ago" 2>/dev/null | grep -i "failed password" | sed -n "s/.*from \([0-9.]*\).*/\1/p" | sort | uniq -c | sort -rn | head -15'
```

### Authorized keys audit
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== AUTHORIZED KEYS ==="; for d in /root/.ssh /home/*/.ssh; do [ -d "$d" ] && echo "$d:" && wc -l "$d/authorized_keys" 2>/dev/null && grep -v "^#" "$d/authorized_keys" 2>/dev/null | while read k; do echo "  $(echo $k | awk "{print \$1,\$2}")"; done; done'
```

### SSH exposure (from network_analysis)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== SSH LISTEN ==="; ss -H -tlnp 2>/dev/null | grep ":22 "; echo "=== UFW SSH ==="; ufw status 2>/dev/null | grep -i ssh || echo "ufw not managing ssh"'
```

## Analysis

### sshd_config
- **`PermitRootLogin yes`**: CRITICAL — root login over SSH is a prime target.
- **`PasswordAuthentication yes`**: HIGH — password brute-force surface; enforce `PubkeyAuthentication yes` only.
- **`PermitEmptyPasswords yes`**: CRITICAL — allows login with empty password.
- **`MaxAuthTries > 6`**: increases brute-force window; default 6 is reasonable.
- **Weak ciphers/MACs/Kex** (`Ciphers` contains `aes128-cbc`, `3des-cbc`, `arcfour`; `MACs` contains `hmac-md5`, `hmac-sha1-96`; `KexAlgorithms` contains `diffie-hellman-group1-sha1`): MEDIUM — downgrade attacks possible.
- **`HostKeyAlgorithms` includes `ssh-rsa`**: SHA-1 based; prefer `ssh-ed25519` / `rsa-sha2-512`.
- **`ClientAliveInterval 0`**: no keepalive; dead connections linger.
- **`AllowUsers`/`AllowGroups` not set**: any valid user/key can login; restrict if possible.

### fail2ban
- **Not installed / not running**: no brute-force mitigation; HIGH if SSH exposed.
- **No `sshd` jail** or `sshd` jail not enabled: SSH brute-force unmitigated.
- **`maxretry > 5`** / `findtime` too long / `bantime` too short (< 1h): weak mitigation.
- **`banaction = iptables-multiport`** (default) vs `nftables`: verify matches host firewall backend.
- **No `recidive` jail**: repeat offenders not escalated.
- **Ban count = 0** but logs show failures: fail2ban not processing logs (wrong logpath / backend).

### SSH exposure
- **Port 22 on 0.0.0.0/0** + no fail2ban + password auth: CRITICAL brute-force target.
- **Non-standard port only** (obscurity) without other hardening: LOW value alone.

### Authorized keys
- **> 20 keys per user**: key sprawl; rotation/review needed.
- **Keys without `from=` restriction** on shared accounts: MEDIUM.

## Thresholds

| Metric | NORMAL | WATCH | WARNING | CRITICAL |
|--------|--------|-------|---------|----------|
| PermitRootLogin | no | no | yes | yes |
| PasswordAuthentication | no | no | yes | yes |
| fail2ban sshd jail | enabled | enabled | disabled | disabled |
| fail2ban bantime | >= 1h | >= 30m | < 30m | < 10m |
| SSH on 0.0.0.0 + no fail2ban | no | no | yes | yes |

## False Positives
- Non-standard SSH port (e.g., 2222) reduces automated scans but is NOT a substitute for key-only auth + fail2ban.
- `PasswordAuthentication yes` with `AllowUsers` restricting to a single service account may be intentional.

## Evidence
- `sshd-config.txt`, `hostkeys.txt`, `fail2ban-status.txt`, `fail2ban-config.txt`, `ssh-authlog.txt`, `authorized-keys.txt`, `ssh-exposure.txt`

## Security
Read-only. Never modify `sshd_config`, `fail2ban` jails, or `authorized_keys` (Level 3).