---
name: ingress-nginx-analysis
area: ingress-nginx
description: Inventory and analysis of an ingress-nginx deployment: which annotations/features are ACTUALLY used today.
purpose: Build a feature inventory from real Ingress objects, not docs. Understand what the ingress controller is doing.
safety: L1
prerequisites:
  - "kubernetes cluster reachable"
applies_when:
  - "kubectl get ingress -A returns objects with spec.ingressClassName == nginx OR annotations nginx.ingress.kubernetes.io/*"
inputs: []
discovery:
  - "kubectl get ingress -A -o custom-columns=NS:.metadata.namespace,NAME:.metadata.name,CLASS:.spec.ingressClassName,HOSTS:.spec.rules[*].host,TLS:.spec.tls[*].hosts --no-headers"
  - "kubectl get ingress -A -o yaml"
tests:
  - "grep annotations nginx.ingress.kubernetes.io/*  -> aggregate distinct keys"
  - "confirm controller presence: kubectl get pods -A | grep -i ingress-nginx; kubectl get ns | grep ingress-nginx"
evidence_artifacts:
  - "36_ingress_nginx_presence.yml"
  - "37_ingress_annotations.yml"
  - "41_ingress_yaml.yml"
interpretation: |
  Build a feature set from the distinct nginx annotations actually present:
    cert-manager.io/cluster-issuer     -> controller-independent TLS (OK under any ingress)
    enable-modsecurity / modsecurity-snippet / modsecurity-transaction-id -> WAF (ModSecurity/OWASP CRS)
    rewrite-target (/\$N) + use-regex       -> regex path rewrite with capture groups
    whitelist-source-range                   -> IP allowlist
    force-ssl-redirect                       -> HTTP->HTTPS redirect
    proxy-buffer-size / proxy-buffers-number / proxy-busy-buffers-size -> upstream buffering (often needed for apps with large headers)
    configuration-snippet / server-snippet   -> arbitrary nginx config injection (security risk)
    auth-type / auth-secret / auth-realm     -> basic auth / external auth
    proxy-body-size / proxy-read-timeout     -> limits/timeouts
  If the controller (pods/svc/ns/CRD/validating-webhook) is ABSENT but Ingress
  objects remain, they are ORPHANED unless another controller honors them.
  Mark WAF as REMOVED if no equivalent is active.
risk_model: |
  WAF removal on a public API gateway = CRITICAL security regression.
  Capture-group rewrite-target /\$2 with no equivalent in the routing layer = HIGH (broken routing).
  Orphaned Ingress objects left behind = MEDIUM (drift/conflict).
remediation_template: ~
references:
  - "https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/"
  - "https://kubernetes.github.io/ingress-nginx/user-guide/modsecurity/"
---

# ingress-nginx Analysis

The point: do NOT assume "Ingress is just Ingress". Aggregate the
REAL annotations from `kubectl get ingress -A -o yaml`. Each distinct annotation
is a feature. ModSecurity is the canonical one that may have no equivalent
in alternative controllers.
