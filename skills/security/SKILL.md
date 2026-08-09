---
name: security-analysis
area: security
description: Defensive security posture review of a Linux host + Kubernetes cluster: SSH, privilege surface, exposure, segmentation, pod security, secrets metadata.
purpose: Surface real exposure and gaps; avoid flagging unusual-but-intended config as a vuln (low false-positive rate).
safety: L1
prerequisites:
  - "SSH access + kubectl access"
applies_when:
  - "always"
inputs: []
discovery:
  - "cat /etc/ssh/sshd_config | grep -iE 'PermitRootLogin|PasswordAuthentication|PubkeyAuthentication|PermitEmptyPasswords|Port|KbdInteractive|X11Forwarding|AllowTcpForwarding|Protocol'"
  - "ss -H -tlnp | grep -E ':22 |:2222 '"
  - "ls -la /root/.ssh /home/*/.ssh 2>/dev/null; wc -l authorized_keys"
  - "getent passwd | awk -F: '{... uid==0 / shell / ...}'"
  - "kubectl get namespaces -o jsonpath=... pod-security.kubernetes.io/enforce"
  - "kubectl get networkpolicy -A"
  - "kubectl get clusterrolebinding -o jsonpath=... | grep -i admin"
  - "kubectl get pods -A -o jsonpath='{..securityContext.privileged}'"
  - "kubectl get pods -A -o jsonpath='{..hostNetwork}' ; '{..hostPath}'"
  - "kubectl get secret -A --field-selector type=kubernetes.io/tls (names only)"
tests:
  - "openssl s_client -connect <host>:443 -servername <vhost> </dev/null 2>/dev/null | openssl x509 -noout -issuer -subject -dates"
  - "curl -skI <vhost> -> TLS + headers (HSTS?)"
evidence_artifacts:
  - "05_users.yml"
  - "06_passwd.yml"
  - "07_groups.yml"
  - "08_sudo.yml"
  - "18_listening.yml"
  - "40a_clusterissuer.yml"
  - "43_netpol_pvc_sc.yml"
  - "49_etcd_rbac.yml"
interpretation: |
  SSH: root login allowed + password auth = HIGH. Pubkey-only = good. Non-standard ports = obscurity not security.
  authorized_keys count > hosts using them = key sprawl / orphan keys.
  PodSecurity not enforced (no pod-security.kubernetes.io/enforce label) = pods may run privileged/hostPath.
  No NetworkPolicy = all pods <-> all pods (no east-west segmentation).
  Secrets: report metadata (namespace/name/type) ONLY; values redacted upstream by scripts/redact.sh.
  TLS: cert-manager or equivalent auto-renewal = good; missing HSTS at edge = MEDIUM.
  Admin UIs on public vhosts without IP allowlisting = MEDIUM (should be restricted).
risk_model: |
  WAF removed on public API gateway = CRITICAL.
  Password SSH + root = HIGH.
  No PSA + no NetworkPolicy = MEDIUM.
  allowSnippetAnnotations = MEDIUM.
remediation_template: |
  WHAT: ...
  WHY: ...
  HOW: ... (Level 3 - requires operator approval; this skill ONLY proposes)
  RISK: ...
  PRIORITY: ...
  VALIDATION: ... (read-only check after change)
  ROLLBACK: ...
references:
  - "https://kubernetes.io/docs/concepts/security/pod-security-standards/"
  - "https://www.cisecurity.org/benchmark/kubernetes"
---

# Security Analysis

Defensive-first. Never report a port as "exposed vulnerable" without: process
context + binding address (0.0.0.0 vs 127.0.0.1) + intended purpose + auth +
exposure path to the internet. Apply the false-positive gate (see AGENTS.md).
