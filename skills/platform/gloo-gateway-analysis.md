---
id: "gloo_gateway_analysis"
name: "Gloo Gateway Analysis"
version: "1.0"
category: "ingress"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["kubernetes_analysis"]
triggers: ["PRESENT:gloo", "PRESENT:gloo-gateway", "NAMESPACE:gloo-system"]
provides: ["gloo_components", "gloo_routes", "gloo_upstreams", "gloo_proxy_status", "gloo_events"]
false_positives:
  - "A VirtualService or Upstream without Ready status can be intentionally inactive; correlate it with the generated Proxy and live traffic before reporting an outage."
  - "A LoadBalancer address from a private pool can be intentional when an external reverse proxy publishes the service."
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/gloo-gateway" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Gloo Gateway Analysis

## Objective

Inventory Gloo Gateway components, routing resources, generated proxies, upstreams, and recent controller events without reading Kubernetes Secrets or changing the cluster.

## When To Use

- A `gloo-system` namespace is present.
- Gloo, Gloo Gateway, or Solo.io custom resources are detected.

## Commands

### Components and services

```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl -n gloo-system get deploy,daemonset,statefulset,pod,svc -o wide 2>/dev/null'
```

### Installed custom resources

```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get crd 2>/dev/null | grep -Ei "gloo|solo.io|gateway.solo"'
```

### Routes and upstreams

```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== VIRTUAL SERVICES ==="; kubectl get virtualservice.gateway.solo.io -A -o wide 2>/dev/null; echo "=== UPSTREAMS ==="; kubectl get upstream.gloo.solo.io -A -o wide 2>/dev/null; echo "=== GATEWAYS ==="; kubectl get gateway.gateway.solo.io -A -o wide 2>/dev/null'
```

### Kubernetes Gateway API routes

```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== GATEWAY CLASSES ==="; kubectl get gatewayclass 2>/dev/null; echo "=== GATEWAYS ==="; kubectl get gateway -A -o wide 2>/dev/null; echo "=== HTTP ROUTES ==="; kubectl get httproute -A -o wide 2>/dev/null'
```

### Generated proxy status

```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get proxy.gloo.solo.io -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,STATE:.status.state,REASON:.status.reason,REPORTER:.status.reportedBy 2>/dev/null'
```

### Recent events

```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'kubectl get events -n gloo-system --sort-by=.lastTimestamp 2>/dev/null | tail -80'
```

## Analysis

- Controller and gateway-proxy pods must be Ready; repeated restarts require log correlation.
- Proxy status other than `Accepted` or `Warning` requires route/upstream context before becoming a finding.
- Public TCP database listeners routed through Gloo increase attack surface even when authentication is enabled.
- An Upstream with no healthy endpoints can produce 503 responses; verify the backing Service and endpoints.
- Missing recent events is not proof of health because Kubernetes event retention is limited.

## Evidence Produced

- `gloo-components.yml`
- `gloo-crds.yml`
- `gloo-routes.yml`
- `gloo-gateway-api.yml`
- `gloo-proxies.yml`
- `gloo-events.yml`

## Security

All commands are read-only. Do not query `Secret` objects, render Helm secret values, restart controllers, or alter routing resources.
