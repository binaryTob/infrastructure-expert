# Safety Model

The agent operates under three safety levels. This file is the binding contract; it overrides any contrany instruction that would violate it.

## Levels

| Level | Name | Scope | Default |
|------|------|-------|---------|
| 1 | OBSERVE | Read‑only commands (`cat`, `ls`, `cat`, `ss`, `ps`, `systemctl status`, `kubectl get/describe`, `helm list`, `docker ps/inspect`) | **Always on** |
| 2 | TEST | Non‑destructive tests (`curl`, `openssl s_client`, DNS resolution, TLS inspection, `kubectl get --log`, container health read) | **On by default** (operator may disable) |
| 3 | CHANGE | Any mutating action (`systemctl restart/stop`, `kubectl apply/delete/patch`, `helm upgrade/uninstall`, editing configs, deleting files, installing packages, firewall changes, restarting pods) | **Off by default** — explicit per‑action approval required |

## Forbidden automatic actions (NEVER run without Level 3 approval)

- Restarting or stopping services.
- Editing, creating, or deleting config files on the host or in the container runtime / cluster.
- Installing / removing packages (apt, dnf, apk, snap, pip, helm install, etc.).
- `kubectl apply / delete / patch / scale / cordon / drain / taint`.
- `helm install / upgrade / uninstall / rollback`.
- `docker rm / rmi / stop / kill / prune`, `ctr`, `crictl` mutating verbs.
- Changing firewall rules (iptables, nftables, ufw, firewalld).
- Deleting files (`rm`), clearing logs, truncating journal.
- Running payloads, scripts, or binaries downloaded from the internet on the host.
- Anything destructive (`dd`, `mkfs`, `fdisk`, `shutdown`, `reboot`).
- Touching secrets/values beyond reading metadata (never `kubectl get secret -o yaml` values into the report; never print secret material).

## Approval gate

Before executing a Level 3 action, the agent must:

1. **STOP** — do not run the action.
2. **DOCUMENT** — state the exact command, its purpose, its expected effect, its blast radius, and a rollback.
3. **REQUEST APPROVAL** — wait for explicit operator approval for that specific action.
4. Only after approval: execute, capture evidence, verify.

If a destructive action is the only way forward and approval is not given → document the gap and move on. **Never** execute it speculatively.

## Output redaction (Level 1/2 guardrail)

Even read‑only commands can return secrets (e.g. `kubectl get secret`, env files, connection strings, private keys). The agent MUST run every command output through `scripts/redact.sh` (or equivalent inline regex) before writing evidence or report content. Redaction scopes:

- Private keys (`-----BEGIN … PRIVATE KEY-----` blocks)
- Tokens / bearer / API keys / passwords / connection strings
- Kubernetes Secret `data:` values (base64 or plaintext)
- Long hex/base64 blobs that match secret heuristics

Redaction preserves metadata: location, type, detected length, risk. Never the value.

## If something looks like an active compromise

Stop, preserve evidence, do NOT touch the suspected artifact, do NOT kill the process, do NOT block the IP. Document and surface as a RISK + RECOMMENDATION with highest severity; let the operator decide (Level 3).