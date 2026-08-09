---
name: networking-analysis
area: networking
description: Map the host + cluster network: interfaces, routes, listening ports, firewall, edge ingress exposure, port->process->service->container links, CNI.
purpose: Build the data-plane edges of the infrastructure graph and detect unintended exposure.
safety: L1
prerequisites: ["SSH access"]
applies_when: ["always"]
inputs: []
discovery:
  - "ip -br addr; ip -o addr"
  - "ip route; ip -6 route"
  - "cat /etc/resolv.conf; cat /etc/hosts"
  - "ss -H -tlnp; ss -H -ulnp"
  - "ss -H -tnp state established | head -60"
  - "ufw status verbose; iptables -S; nft list ruleset"
  - "kubectl get svc -A; kubectl get pods -A -o wide"
  - "kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.name} hostNetwork={.spec.hostNetwork}{\"\n\"}{end}'"
tests:
  - "curl -skI --resolve <host>:443:127.0.0.1 https://<host>/"
evidence_artifacts:
  - "15_net_ifaces.yml"
  - "16_routes.yml"
  - "17_dns.yml"
  - "18_listening.yml"
  - "19_established.yml"
  - "20_firewall.yml"
  - "22_listening_proc.yml"
interpretation: |
  Map each listening socket: addr:port -> PID -> process -> (container? pod? service?).
  0.0.0.0 binding = external; 127.0.0.1 = local only. CNI=flannel -> 10.244.0.0/16 pod CIDR.
   Edge: nodeIP:80/443 (hostPort) -> ingress controller pods -> route/Ingress -> svc -> pod.
  No host firewall (ufw disabled / iptables default) = rely on cloud/security-group + k8s. Verify externally.
risk_model: |
  Admin UIs on public vhosts without allowlist = MEDIUM-HIGH.
  Management ports exposed to 0.0.0.0 without firewall = MEDIUM.
references:
  - "man ss ip; https://kubernetes.io/docs/concepts/services-networking/"
---

# Networking Analysis

Always relate PORT -> PROCESS -> SERVICE -> CONTAINER -> APPLICATION. A bare
listening port is not a finding.