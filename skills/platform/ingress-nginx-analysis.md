---
id: "ingress_nginx_analysis"
name: "Ingress-Nginx Analysis"
version: "1.0"
category: "ingress"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["kubernetes_analysis"]
triggers: ["PRESENT:kubectl"]
provides: ["ingress_features", "ingress_annotations", "waf_status"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/ingress-nginx" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Ingress-Nginx Analysis

Inventory and analysis of ingress-nginx deployment: which annotations/features are actually used.

## Commands

### Ingress inventory
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get ingress -A -o custom-columns=NS:.metadata.namespace,NAME:.metadata.name,CLASS:.spec.ingressClassName,HOSTS:.spec.rules[*].host,TLS:.spec.tls[*].hosts --no-headers 2>/dev/null'
```

### All ingress YAML (for annotation analysis)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get ingress -A -o yaml 2>/dev/null'
```

### Controller presence
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get pods -A 2>/dev/null | grep -i ingress-nginx; echo ===; kubectl get ns 2>/dev/null | grep -i ingress-nginx; echo ===; kubectl get validatingwebhookconfiguration 2>/dev/null | grep -i ingress-nginx'
```

### Distinct annotations used
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get ingress -A -o yaml 2>/dev/null | grep -oP "nginx\.ingress\.kubernetes\.io/[a-z-]+" | sort -u'
```

## Analysis
Build feature set from actually present nginx annotations:
- `enable-modsecurity` / `modsecurity-snippet` -> WAF (ModSecurity/OWASP CRS)
- `rewrite-target` with `use-regex` -> regex path rewrite with capture groups
- `whitelist-source-range` -> IP allowlist
- `force-ssl-redirect` -> HTTP->HTTPS redirect
- `configuration-snippet` / `server-snippet` -> arbitrary nginx config injection (security risk)
- `auth-type` / `auth-secret` -> basic auth / external auth

If controller is ABSENT but Ingress objects remain, they are ORPHANED.
WAF removal on public API gateway without replacement = CRITICAL.

## Security
Read-only.
