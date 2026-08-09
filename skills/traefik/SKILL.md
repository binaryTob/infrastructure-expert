---
name: traefik-analysis
area: traefik
description: Deep read-only analysis of a Traefik (v3) ingress deployment: provider config, entrypoints, middlewares, TLS, compat providers.
purpose: Verify the Traefik deployment is correctly configured and not introducing routing ambiguities or security regressions.
safety: L1
prerequisites:
  - "traefik namespace / Helm release present"
applies_when:
  - "command -v helm; helm list -A | grep traefik"
  - "kubectl get ns | grep -i traefik"
inputs: []
discovery:
  - "helm get values traefik -n traefik"
  - "kubectl -n traefik get deploy,ds,svc -o wide"
  - "kubectl -n traefik get deploy traefik -o jsonpath='{..args}' (container args)"
  - "kubectl get ingressroute -A -o yaml"
  - "kubectl get middleware -A -o yaml"
  - "kubectl get tlsstore,tlsoption -A 2>/dev/null"
tests:
  - "curl -skI --resolve <host>:443:127.0.0.1 https://<host>/  (per host) -> Server/cert/redirect/404"
  - "curl -sI --resolve <host>:80:127.0.0.1 http://<host>/      -> HTTP->308 HTTPS"
  - "compare referenced service names in IngressRoute vs kubectl get svc -A -> 503 if missing"
evidence_artifacts:
  - "33_traefik_deploy.yml"
  - "34_traefik_values.yml"
  - "35_traefik_svc_yaml.yml"
  - "38_ingressroute_yaml.yml"
  - "39_middleware_yaml.yml"
  - "44_http_ingressroutes.yml"
  - "45_reachability.yml"
  - "48_api_paths.yml"
interpretation: |
  Providers (values.providers.*):
    kubernetesCRD.enabled       -> IngressRoute/Middleware (native Traefik)
    kubernetesIngress.enabled   -> standard Ingress via Traefik
    kubernetesIngressNGINX.enabled -> compat provider honoring Ingress with nginx annotations
  If both CRD and IngressNGINX are on AND a host has BOTH an
  Ingress and an IngressRoute -> DUAL ROUTING. CRD usually wins;
  flag drift/conflict risk. The Ingress objects become redundant.
  hostNetwork:false + service.enabled:false + DaemonSet + hostPort -> edge via nodeIP:80/443.
  forwardedHeaders.insecure:true -> trusts X-Forwarded-* from any source (spoof risk if a hop exists).
  allowSnippetAnnotations:true -> any Ingress owner can inject Traefik config (privilege escalation within ingress).
  TLS: cert-manager issues the secret referenced by IngressRoute.tls.secretName -> cert path is controller-independent (good).
  Reachability:
    404 root on a vhost with no catch-all route = expected.
    503 for a specific path = the backend service named in the IngressRoute does NOT exist (stale/renamed) -> configuration defect.
    401/200/302 from the app after routing = routing WORKS (app-level response, not a Traefik failure).
    403 on a whitelisted host = ipAllowList middleware working.
risk_model: |
  IngressRoute -> missing service (503) on a public vhost = HIGH availability.
  Dual routing (Ingress + IngressRoute same host) = MEDIUM drift.
  WAF gone with no replacement = CRITICAL.
  allowSnippetAnnotations:true = MEDIUM security.
  forwardedHeaders.insecure:true = LOW-MEDIUM (depends on upstream hops).
remediation_template: ~
references:
  - "https://doc.traefik.io/traefik/v3.7/routing/providers/kubernetes-ingress/"
  - "https://doc.traefik.io/traefik/v3.7/routing/providers/kubernetes-crd/"
---

# Traefik Analysis

Always corroborate config claims with reachability (curl). 503 != the feature is
broken; 503 == the named backend service is absent. Distinguish Traefik-level
(404/308/503/default-cert) from app-level (200/302/401/app-404) responses.
