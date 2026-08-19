---
id: "tls_certificate_analysis"
name: "TLS Certificate Analysis"
version: "1.0"
category: "tls"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "network_analysis"]
triggers: ["PRESENT:http_server", "PRESENT:apache2", "PRESENT:httpd", "PRESENT:nginx", "PRESENT:letsencrypt"]
provides: ["cert_expiry", "cert_issuer", "cert_sans", "cert_chain", "tls_protocols", "cert_host_match"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/tls" }
  SSH_TARGET: { type: "string", required: true }
  WARN_DAYS: { type: "integer", default: 30, description: "Umbral de dias para aviso de expiracion" }
output: { format: "json", schema: "output_schema" }
---

# TLS Certificate Analysis

## Objective
Detect every TLS certificate on the host (Let's Encrypt / custom), check expiry,
issuer, SANs, and hostname match against the configured vhosts. Expired or soon-to-expire
certificates are a top cause of silent production outages.

## Commands

### Locate certificates (Let's Encrypt + system trust + custom)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== LE LIVE ==="; ls -1 /etc/letsencrypt/live/ 2>/dev/null; echo; echo "=== CERTBOT ==="; command -v certbot >/dev/null && certbot certificates 2>/dev/null; echo; echo "=== CERT FILES ==="; find /etc/letsencrypt/live /etc/ssl /etc/nginx /etc/apache2 /etc/httpd -type f \( -name "*.pem" -o -name "*.crt" \) 2>/dev/null | head -60'
```

### Expiry / issuer / SAN per certificate (LE live dirs)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for d in /etc/letsencrypt/live/*/; do [ -f "$d/fullchain.pem" ] || continue; dom=$(basename "$d"); end=$(openssl x509 -enddate -noout -in "$d/fullchain.pem" 2>/dev/null | cut -d= -f2-); days=$(openssl x509 -checkend $(( {{WARN_DAYS}} * 86400 )) -noout -in "$d/fullchain.pem" 2>/dev/null && echo "OK" || echo "EXPIRING"); iss=$(openssl x509 -issuer -noout -in "$d/fullchain.pem" 2>/dev/null | sed "s/issuer=//"); sans=$(openssl x509 -noout -ext subjectAltName -in "$d/fullchain.pem" 2>/dev/null); echo "$dom | expires=$end | $days | issuer=$iss"; echo "    SAN: $sans"; done'
```

### Arbitrary certificate files (non-LE)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'find /etc/ssl /etc/nginx /etc/apache2 /etc/httpd -type f \( -name "*.pem" -o -name "*.crt" \) 2>/dev/null | while read f; do openssl x509 -in "$f" -noout -subject -enddate 2>/dev/null && echo "  file=$f"; done | head -80'
```

### TLS protocol + cipher support (external perspective, per domain)
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'for d in /etc/letsencrypt/live/*/; do dom=$(basename "$d"); [ "$dom" = "*" ] && continue; echo "=== $dom ==="; echo | timeout 8 openssl s_client -connect "$dom:443" -servername "$dom" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null; echo "TLS1.2: $(timeout 6 openssl s_client -connect $dom:443 -servername $dom -tls1_2 </dev/null 2>/dev/null | grep -c "CONNECTED")"; echo "TLS1.3: $(timeout 6 openssl s_client -connect $dom:443 -servername $dom -tls1_3 </dev/null 2>/dev/null | grep -c "CONNECTED")"; done'
```

### Hostname vs cert SAN match (vhosts vs cert names)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== SERVERNAMES ==="; grep -rhoiE "ServerName [A-Za-z0-9.\-]+" /etc/apache2 /etc/httpd 2>/dev/null | awk "{print \$2}" | sort -u; echo; echo "=== CERT DOMAINS ==="; for d in /etc/letsencrypt/live/*/; do basename "$d"; done'
```

## Analysis

- **Expired / < {{WARN_DAYS}} days**: WARNING now, CRITICAL at expiry — a cert that expires takes the whole domain down with a browser trust error (not a 5xx, but a full outage).
- **Issuer**: Let's Encrypt (short 90-day lifetime) MUST have auto-renewal (`certbot renew` cron/timer) or it will expire. Check `systemd_analysis` timers for `certbot` / `snap.certbot.renew`.
- **SAN mismatch**: vhost `ServerName` not in the cert SAN -> browser warning / broken TLS.
- **TLS 1.0/1.1 still enabled**: obsolete protocols; browsers and PCI require >= 1.2.
- **TLS 1.3 disabled on a modern stack**: minor optimization gap, not a risk.

## False Positives
- A cert in `/etc/ssl` that is a CA bundle or client cert is NOT a server outage risk — only flag SAN/expiry for certs actually referenced by a vhost (`SSLCertificateFile`).
- Staging Let's Encrypt certs (`issuer=...Fake LE...`) will fail in browsers but are intentional in test environments.

## Evidence
- `cert-list.txt`, `cert-expiry.txt`, `cert-files.txt`, `tls-protocols.txt`, `host-match.txt`

## Security
Read-only. Never modify certs or run `certbot renew --force` (that mutates). Report expiry as a RECOMMENDATION with the exact renewal command for the operator.
