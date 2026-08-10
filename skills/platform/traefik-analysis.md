---
id: "traefik_analysis"
name: "Traefik Analysis"
version: "1.0"
category: "ingress"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["kubernetes_analysis"]
triggers: ["PRESENT:traefik"]
provides: ["traefik_providers", "entrypoints", "middlewares", "tls_analysis"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/traefik" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Traefik Analysis

Deep read-only analysis of Traefik (v2/v3) ingress deployment: provider config, entrypoints, middlewares, TLS, compat providers.

## Commands

### Helm values
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'helm get values traefik -n traefik 2>/dev/null || helm list -A 2>/dev/null | grep traefik'
```

### Deployment details
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl -n traefik get deploy,ds,svc -o wide 2>/dev/null; echo; kubectl -n traefik get deploy traefik -o jsonpath='"'"'{..args}'"'"' 2>/dev/null'
```

### IngressRoutes
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get ingressroute -A -o yaml 2>/dev/null'
```

### Middlewares
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get middleware -A -o yaml 2>/dev/null'
```

### TLS stores / options
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get tlsstore,tlsoption -A 2>/dev/null; echo; kubectl get certificate -A 2>/dev/null'
```

### Reachability test
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'for ing in $(kubectl get ingressroute -A --no-headers -o custom-columns=HOSTS:.spec.routes[*].match 2>/dev/null | head -10); do host=$(echo "$ing" | grep -oP "Host\(\\K[^)]+" | head -1); [ -n "$host" ] && curl -skI --connect-timeout 3 --resolve "$host:443:127.0.0.1" "https://$host/" 2>/dev/null | head -5; done'
```

## Analysis
Providers (from Helm values):
- `kubernetesCRD.enabled` -> IngressRoute/Middleware (native Traefik)
- `kubernetesIngress.enabled` -> standard Ingress via Traefik
- `kubernetesIngressNGINX.enabled` -> compat provider for nginx annotations
If both CRD and IngressNGINX: host with Ingress + IngressRoute = DUAL ROUTING (CRD usually wins). Flag drift/conflict.
- `hostNetwork:false` + DaemonSet + hostPort -> edge via nodeIP:80/443.
- `forwardedHeaders.insecure:true` -> trusts X-Forwarded-* from any source (spoof risk).
- `allowSnippetAnnotations:true` -> any Ingress owner can inject Traefik config.
Reachability: 503 = backend service absent. 404 = no matching route. 30x = redirect. 2xx = app works.

## Security
Read-only. Flag WAF gaps, dual routing, insecure headers. Never modify Traefik config.
