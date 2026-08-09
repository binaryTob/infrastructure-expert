#!/usr/bin/env bash
# scripts/ssh_exec.sh — READ-ONLY SSH abstraction + evidence recorder
#
# Usage:
#   scripts/ssh_exec.sh <evidence-basename> <category> <safety-level> "<command>"
#   scripts/ssh_exec.sh <evidence-basename> <category> <safety-level> "<command>" <evidence_dir>
#
# Environment (or config/target.json read via scripts/read_target.sh):
#   SSH_HOST, SSH_PORT, SSH_USER, SSH_KEY, CONNECT_TIMEOUT, COMMAND_TIMEOUT
#
# Behaviour:
#   * connects over ssh using the operator's key (no password)
#   * blocks any command matching the Level-3 mutability blocklist
#   * runs the command, captures exit/stdout/stderr
#   * pipes stdout/stderr through scripts/redact.sh
#   * writes a redacted evidence YAML to $EVIDENCE_DIR/<evidence-basename>.yml
#   * prints a short result line + the evidence path to stdout
#
# Exit codes: 0 (ran+recorded, regardless of remote exit), 2 (blocked L3),
#             3 (ssh connect failure), 4 (bad args).
#
# This script NEVER runs Level-3 commands. It refuses them.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

# --- load target config -----------------------------------------------------
HOST="${SSH_HOST:-}"
PORT="${SSH_PORT:-}"
USER="${SSH_USER:-}"
KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
CT="${CONNECT_TIMEOUT:-15}"
TO="${COMMAND_TIMEOUT:-60}"

if [[ -z "$HOST" || -z "$USER" ]]; then
  # try to read config/target.json
  if [[ -f "$ROOT/config/target.json" ]]; then
    get() { python3 - "$ROOT/config/target.json" "$1" <<'PY'
import json,sys,pathlib
d=json.loads(pathlib.Path(sys.argv[1]).read_text())
def digs(o,ks):
    for k in ks:
        if isinstance(o,dict): o=o.get(k)
        else: return ""
    return o if isinstance(o,(str,int)) else ""
print(digs(d, sys.argv[2].split(".")))
PY
}
  fi
  HOST="${HOST:-$(get ssh.host)}"
  PORT="${PORT:-$(get ssh.port)}"
  USER="${USER:-$(get ssh.user)}"
  KEY="${KEY:-$(get ssh.private_key)}"
  KEY="${KEY/#\~/$HOME}"
  CT="${CT:-$(get ssh.connect_timeout)}"
  TO="${TO:-$(get ssh.command_timeout)}"
fi
PORT="${PORT:-22}"
HOST="${HOST:?missing ssh.host}"
USER="${USER:?missing ssh.user}"

# --- args -------------------------------------------------------------------
if [[ $# -lt 4 ]]; then
  echo "usage: $0 <evidence-basename> <category> <safety L1|L2> \"<command>\" [evidence_dir]" >&2
  exit 4
fi
EV_BASE="$1"; CATEGORY="$2"; SAFETY="$3"; CMD="$4"
EV_DIR="${5:-$(scripts/run_id.sh dir)}"

# --- Level-3 mutability blocklist (binding, see SAFETY.md) ------------------
# Refuse anything that mutates the host/cluster. Simple + fail-closed: any
# grep parse error (rc=2) blocks. Defense-in-depth beside the agent context.
is_level3() {
  local lc lc_clean
  # normalize whitespace only; matching is case-insensitive (-i) so keep case.
  lc="$(printf '%s' "$1" | tr -s '[:space:]' ' ')"
  lc="${lc# }"; lc="${lc% }"
  # Remove harmless redirects to /dev/null (discard) before redirect-pattern tests,
  # so `cmd 2>/dev/null` is not mistaken for a truncating redirect to a real file.
  lc_clean="$(printf '%s' "$lc" | sed -E 's/[012]?>>?[[:space:]]*\/dev\/null//g; s/<[[:space:]]*\/dev\/null//g')"
  local p rc
  local patterns=(
    '(^|[[:space:]])(systemctl|service)[[:space:]]+(\S+[[:space:]]+)?(start|stop|restart|reload|enable|disable|mask|unmask|daemon-reload|reset-failed)([[:space:]]|$)'
    '(^|[[:space:]])(apt|apt-get|yum|dnf|zypper|apk|snap|pip|pip3|npm|gem)[[:space:]]+(install|remove|purge|upgrade|autoremove|update[[:space:]]+-y)([[:space:]]|$)'
    '(^|[[:space:]])(helm)[[:space:]]+(install|upgrade|uninstall|rollback|delete|pull)([[:space:]]|$)'
    '(^|[[:space:]])(kubectl)[[:space:]].*(apply|delete|patch|scale|cordon|drain|taint|replace|edit|label|annotate|approve|cp|debug)([[:space:]]|$)'
    '(^|[[:space:]])(kubectl)[[:space:]]+rollout[[:space:]]+(restart|undo)([[:space:]]|$)'
    '(^|[[:space:]])(k3s)[[:space:]]+(uninstall|kill)'
    '(^|[[:space:]])(kubeadm)[[:space:]]+(reset|init|join)'
    '(^|[[:space:]])(docker)[[:space:]]+(rm|rmi|stop|kill|pause|restart|rename)[[:space:]]'
    '(^|[[:space:]])(docker)[[:space:]]+prune([[:space:]]|$)'
    '(^|[[:space:]])(docker[[:space:]]+(network|volume)[[:space:]]+(rm|prune))'
    '(^|[[:space:]])(ctr|crictl|nerdctl)[[:space:]]+(rm|rmi|stop|kill|remove|run)'
    '(^|[[:space:]])(iptables|ip6tables)[[:space:]]+(-[AFDIXZ]|--insert|--append|--delete|--flush|--policy|--zero)'
    '(^|[[:space:]])(iptables-restore|ip6tables-restore)([[:space:]]|$)'
    '(^|[[:space:]])(nft)[[:space:]]+(add|delete|flush|insert)'
    '(^|[[:space:]])(ufw)[[:space:]]+(enable|disable|allow|deny|delete|reset)'
    '(^|[[:space:]])(firewall-cmd)[[:space:]].*(--add|--remove|--permanent)'
    '(^|[[:space:]])(rm|rmdir)[[:space:]]'
    '(^|[[:space:]])(truncate)[[:space:]]+-s'
    '(^|[[:space:]])(dd)[[:space:]].*of='
    '(^|[[:space:]])(mkfs[0-9a-z]*|fdisk|parted|wipefs)[[:space:]]'
    '(^|[[:space:]])(parted)[[:space:]].*(mklabel|rm|mkpart)'
    '(^|[[:space:]])(shutdown|reboot|halt|poweroff|telinit)([[:space:]]|$)'
    '(^|[[:space:]])(init)[[:space:]]+[06]'
    '(^|[[:space:]])(chmod|chown|chgrp|chattr|setfacl)[[:space:]]'
    '(^|[[:space:]])(umount|swapoff)[[:space:]]'
    '(^|[[:space:]])(mount)[[:space:]]+(-[a-z]|/[[:alnum:]])'
    '(^|[[:space:]])(swapon)[[:space:]]+(/|-a)([[:space:]]|$)'
    '(^|[[:space:]])tee[[:space:]]+(/etc/|/opt/|/usr/local/|/etc/systemd/|/root/|/home/)'
    '(^|[[:space:]])(journalctl)[[:space:]].*--vacuum'
    '(^|[[:space:]])(find)[[:space:]].*-delete([[:space:]]|$)'
    '(^|[[:space:]])(crontab)[[:space:]]+(-r|-e)'
    '(^|[[:space:]])(visudo|update-grub|grub-install)([[:space:]]|$)'
    '(^|[[:space:]])[0-9]?>[[:space:]]*[^&[:space:]]'
    '(^|[[:space:]])2>[[:space:]]*[^&[:space:]]'
  )
  for p in "${patterns[@]}"; do
    printf '%s' "$lc_clean" | grep -Eqi "$p"; rc=$?
    if [ "$rc" -eq 0 ]; then return 0; fi
    if [ "$rc" -eq 2 ]; then echo "[is_level3] pattern error -> fail-closed BLOCK: $p" >&2; return 0; fi
  done
  return 1
}

if is_level3 "$CMD"; then
  cat >&2 <<MSG
[ssh_exec] BLOCKED (Level-3 mutability guard): $CMD
This command appears to mutate the host/cluster. Level-3 actions require
explicit per-action operator approval. See SAFETY.md. If this is a false
positive, run the command manually or relax the guard explicitly.
MSG
  exit 2
fi

mkdir -p "$EV_DIR"

EV_PATH="$EV_DIR/$EV_BASE.yml"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
REMOTE_OUT="$(mktemp)"; REMOTE_ERR="$(mktemp)"; REMOTE_RC=0

SSH_OPTS=(
  -o BatchMode=yes
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout="${CT}"
  -o ServerAliveInterval=5
  -o ServerAliveCountMax=3
  -o LogLevel=ERROR
  -i "$KEY"
  -p "$PORT"
)

timeout "${TO}" ssh "${SSH_OPTS[@]}" "$USER@$HOST" "$CMD" >"$REMOTE_OUT" 2>"$REMOTE_ERR" || REMOTE_RC=$?

# capture remote identity proof on first call of a run (cheap, read-only)
if [[ ! -f "$EV_DIR/00_connectivity.yml" && "$EV_BASE" != "00_connectivity" ]]; then
  :
fi

REDACTED_OUT="$("$HERE/redact.sh" -s <"$REMOTE_OUT")"
REDACTED_ERR="$("$HERE/redact.sh" -s <"$REMOTE_ERR")"

{
  printf 'id: %s\n' "$EV_BASE"
  printf 'run_id: %s\n' "$(basename "$EV_DIR")"
  printf 'timestamp: %s\n' "$TS"
  printf 'host: %s\n' "${SSH_HOST:-$HOST}"
  printf 'safety_level: %s\n' "$SAFETY"
  printf 'category: %s\n' "$CATEGORY"
  printf 'command: %s\n' "$CMD"
  printf 'exit_code: %d\n' "$REMOTE_RC"
  printf 'stdout: |\n'
  printf '%s\n' "$REDACTED_OUT" | sed 's/^/  /; s/  $//'
  printf 'stderr: |\n'
  printf '%s\n' "$REDACTED_ERR" | sed 's/^/  /; s/  $//'
  printf 'interpretation: ""\n'
  printf 'confidence: LOW\n'
} >"$EV_PATH"

rm -f "$REMOTE_OUT" "$REMOTE_ERR"

# short stdout line for the agent
N_LINES=$(printf '%s\n' "$REDACTED_OUT" | grep -c . || true)
printf '[ok] rc=%d lines=%d ev=%s :: %s\n' "$REMOTE_RC" "$N_LINES" "$EV_PATH" "$CMD"
exit 0