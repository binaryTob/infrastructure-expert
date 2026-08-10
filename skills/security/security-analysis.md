---
id: "security_analysis"
name: "Security Analysis"
version: "2.0"
category: "security"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["system_inventory", "process_analysis", "network_analysis"]
triggers: []
provides: ["ssh_posture", "privileged_processes", "suspicious_processes", "suspicious_connections", "persistence_indicators"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/security" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Security Analysis

Defensive security posture review of a Linux host + Kubernetes cluster.
This skill CONSUMES evidence from `process_analysis` (all-processes.txt, tree.txt)
and `network_analysis` (listening.txt, established.txt). It does NOT re-run `ps aux`
or `ss -tlnp` — those were already fetched by its dependencies.

## Commands (only what dependencies do NOT already fetch)

### SSH configuration
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'grep -iE "PermitRootLogin|PasswordAuthentication|PubkeyAuthentication|PermitEmptyPasswords|Port|MaxAuthTries|ClientAliveInterval" /etc/ssh/sshd_config 2>/dev/null'
```

### Authorized keys count
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for d in /root/.ssh /home/*/.ssh; do [ -d "$d" ] && echo "$d:" && wc -l "$d/authorized_keys" 2>/dev/null; done'
```

### Sudoers
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'grep -v "^#" /etc/sudoers 2>/dev/null | grep -v "^$"; echo ===; ls -la /etc/sudoers.d/ 2>/dev/null'
```

### Persistence indicators
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== MOTD ==="; ls -la /etc/update-motd.d/ 2>/dev/null; echo "=== PROFILE.D ==="; ls -la /etc/profile.d/ 2>/dev/null; echo "=== SYSTEMD OVERRIDES ==="; ls /etc/systemd/system/*.service.d/ 2>/dev/null; echo "=== SETUID ==="; find / -perm -4000 -type f 2>/dev/null | grep -vE "/usr/bin/|/usr/lib/|/bin/|/sbin/" | head -15'
```

### Login sessions
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'who; w; last -n 10'
```

### Kubernetes security (if present — not covered by kubernetes_analysis)
```bash
# [risk:ro] [mode:auto] [requires:kubectl]
ssh {{SSH_TARGET}} 'echo "=== POD SECURITY ==="; kubectl get namespaces -o jsonpath='"'"'{range .items[*]}{.metadata.name}{"\\t"}{.metadata.labels.pod-security\.kubernetes\.io/enforce}{"\\n"}{end}'"'"' 2>/dev/null; echo "=== PRIVILEGED ==="; kubectl get pods -A -o jsonpath='"'"'{range .items[?(@.spec.containers[*].securityContext.privileged == true)]}{.metadata.namespace}/{.metadata.name}{"\\n"}{end}'"'"' 2>/dev/null; echo "=== HOSTNETWORK ==="; kubectl get pods -A -o jsonpath='"'"'{range .items[?(@.spec.hostNetwork == true)]}{.metadata.namespace}/{.metadata.name}{"\\n"}{end}'"'"' 2>/dev/null'
```

## Analysis (consume evidence from dependencies)
- Read `process/all-processes.txt` and grep for `xmrig|kdevtmpfsi|kinsing|backdoor|reverse`.
- Read `network/listening.txt` and grep for `:22|:2222` (SSH), `:4444|:1337|:31337|:6667` (suspicious).
- Read `network/established.txt` and grep for outbound to suspicious ports.
- Read `discovery/users.txt` for users with shell + root-equivalent.
- SSH root login allowed + password auth = HIGH risk. Pubkey-only = good.
- No PodSecurity enforcement = pods may run privileged/hostPath.
- TLS secrets: report metadata ONLY. Values redacted upstream.

## Evidence
- `ssh-config.txt`, `authorized-keys.txt`, `sudoers.txt`, `persistence.txt`, `sessions.txt`, `k8s-security.txt`

## Security
Read-only. If confirmed threat: flag with CRITICAL severity, do NOT kill process or modify anything. Document and let operator decide (Level 3).