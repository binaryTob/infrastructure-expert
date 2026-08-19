---
id: "dns_analysis"
name: "DNS Analysis"
version: "1.0"
category: "network"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "network_analysis"]
triggers: ["PRESENT:systemd-resolved", "PRESENT:resolvectl", "PRESENT:bind9", "PRESENT:dnsmasq", "PRESENT:unbound"]
provides: ["dns_resolver", "dns_forwarding", "dns_cache", "dns_split", "dnssec", "dns_over_tls", "per_interface_dns"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/dns" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# DNS Analysis

## Objective
Analyze the host's DNS resolution chain: resolver (systemd-resolved, dnsmasq, unbound, bind9),
per-interface DNS, split-DNS, DNSSEC, DNS-over-TLS/HTTPS, and container DNS inheritance.
Critical for diagnosing `EAI_AGAIN`, `ENOTFOUND`, and intermittent connectivity.

## Commands

### Resolver detection + config
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== RESOLVER ==="; systemctl is-active systemd-resolved 2>/dev/null && echo "systemd-resolved: ACTIVE" || echo "systemd-resolved: inactive"; command -v dnsmasq >/dev/null && echo "dnsmasq: present"; command -v unbound >/dev/null && echo "unbound: present"; command -v named >/dev/null && echo "bind9: present"'
```

### systemd-resolved deep dive (if active)
```bash
# [risk:ro] [mode:auto] [requires:systemd-resolved]
ssh {{SSH_TARGET}} 'echo "=== GLOBAL DNS ==="; resolvectl status 2>/dev/null | head -60; echo; echo "=== PER-LINK ==="; resolvectl status 2>/dev/null | grep -A2 "Link " | head -40; echo; echo "=== CACHE STATS ==="; resolvectl statistics 2>/dev/null'
```

### resolv.conf + nsswitch (source of truth)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== RESOLV.CONF ==="; cat /etc/resolv.conf; echo; echo "=== NSSWITCH ==="; grep ^hosts: /etc/nsswitch.conf; echo; echo "=== SYSTEMD-RESOLVED CONF ==="; cat /etc/systemd/resolved.conf 2>/dev/null || echo "no resolved.conf"'
```

### DNSSEC + DoT/DoH
```bash
# [risk:ro] [mode:auto] [requires:systemd-resolved]
ssh {{SSH_TARGET}} 'resolvectl query example.com 2>/dev/null | grep -i "dnssec\|tls" || echo "no DNSSEC/DoT data"'
```

### Split-DNS / per-interface
```bash
# [risk:ro] [mode:auto] [requires:systemd-resolved]
ssh {{SSH_TARGET}} 'for link in $(resolvectl status 2>/dev/null | grep "Link " | awk "{print \$2}"); do echo "=== $link ==="; resolvectl dns "$link" 2>/dev/null; done'
```

### Container DNS inheritance (if docker present)
```bash
# [risk:ro] [mode:auto] [requires:docker]
ssh {{SSH_TARGET}} 'echo "=== DOCKER DNS ==="; cat /etc/docker/daemon.json 2>/dev/null | grep -i dns || echo "no custom DNS"; for c in $(docker ps -q 2>/dev/null | head -5); do name=$(docker inspect --format "{{.Name}}" $c | cut -c2-); dns=$(docker exec $c cat /etc/resolv.conf 2>/dev/null | grep nameserver); echo "$name -> $dns"; done'
```

### External resolution test (health check)
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'for d in google.com cloudflare.com github.com; do echo -n "$d: "; resolvectl query "$d" 2>/dev/null | grep -E "IN A|IN AAAA" | head -1 || dig +short "$d" 2>/dev/null | head -1; done'
```

## Analysis

- **No resolver + no `/etc/resolv.conf`**: resolution will fail or use kernel default (often broken).
- **systemd-resolved inactive + Docker present**: containers inherit host's `/etc/resolv.conf`; if that points to a VPN/Tailscale IP (`100.100.100.100`), external resolution fails inside containers.
- **`DNSSEC=yes` but validation fails**: `resolvectl query` shows `DNSSEC: failed` -> silent resolution failures.
- **Split-DNS misconfigured**: per-link DNS differs from global; VPN leak or intranet not resolving.
- **`DNSOverTLS=yes` but no upstream supports it**: fallback may be silent.
- **Container DNS != host DNS**: app inside container resolves differently than host; `EAI_AGAIN` in container only.

## Thresholds

| Metric | NORMAL | WATCH | WARNING | CRITICAL |
|--------|--------|-------|---------|----------|
| Failed DNSSEC validations | 0 | 0 | 1-5 | >5 |
| Containers with `100.100.100.100` nameserver | 0 | 0 | 1 | >1 |
| Resolution latency (p50) | <50ms | 50-100ms | 100-300ms | >300ms |

## False Positives
- `systemd-resolved` inactive but `resolv.conf` points to a working upstream (e.g., `1.1.1.1`) is fine.
- VPN MagicDNS (`100.100.100.100`) is expected on Tailscale hosts; only flag if containers can't reach it.

## Evidence
- `resolver.txt`, `resolved-status.txt`, `resolv-conf.txt`, `dnssec.txt`, `split-dns.txt`, `container-dns.txt`, `resolution-test.txt`

## Security
Read-only. Never modify `resolved.conf`, `resolv.conf`, or Docker daemon JSON (Level 3).