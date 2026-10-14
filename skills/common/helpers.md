# Common Helpers — Infrastructure Expert

Reusable modules included in skills/workflows through `<!-- MODULE:helpers.name -->`.
Execution is **read-only** over SSH. Do not install, restart or modify anything on the server.

---

## MODULE:helpers.ssh_run

The single entry point for remote commands. Delegate capture and redaction to the
canonical wrapper; skills must not implement their own SSH or write raw remote output.

```bash
# Usage: ssh_run <evidence-id> <category> <L1|L2> <remote-command>
ssh_run() {
  local evidence_id="$1" category="$2" level="$3" cmd="$4"
  scripts/ssh_exec.sh "$evidence_id" "$category" "$level" "$cmd" "{{RUN_DIR}}/evidencia"
}
```

---

## MODULE:helpers.redact

Redaction is centralized in `scripts/redact.py` and invoked by `scripts/ssh_exec.sh`
before evidence is persisted. Do not duplicate regular expressions in skills:
partial implementations diverge and can leak secrets.

---

## MODULE:helpers.detect

Dynamically detect components on the host (read-only).
The workflow uses this to decide which skills to execute and which to skip.

```bash
detect_components() {
  ssh_run discovery-components discovery L1 'for c in systemctl docker docker-compose kubectl helm crictl \
    nginx apache2 httpd apachectl traefik psql mysql mariadb redis-cli mongod node pm2 java python3 go \
    iostat vmstat mpstat pidstat iotop sar tcpdump; do
      command -v "$c" >/dev/null 2>&1 && echo "PRESENT:$c" || echo "ABSENT:$c"
    done
    ss -tulpn 2>/dev/null | grep -qE ":5432\b" && echo "PRESENT:postgresql_socket"
    ss -tulpn 2>/dev/null | grep -qE ":3306\b" && echo "PRESENT:mysql_socket"
    ss -tulpn 2>/dev/null | grep -qE ":6379\b" && echo "PRESENT:redis_socket"
    ss -tulpn 2>/dev/null | grep -qE ":80 |:443 |:8080 |:8443 " && echo "PRESENT:http_server"
    [ -d /etc/letsencrypt/live ] && echo "PRESENT:letsencrypt"
    command -v certbot >/dev/null 2>&1 && echo "PRESENT:certbot"
    [ -f /etc/os-release ] && . /etc/os-release && echo "OS:${PRETTY_NAME:-unknown}"
    systemd-detect-virt 2>/dev/null || true'
}
```

---

## MODULE:helpers.snapshot_loop

Time-series snapshot loop without artificial load (`sleep` + measurement only).

```bash
snapshot_loop() {
  local base_id="$1" category="$2" cmd="$3" n="${SAMPLE_COUNT:-4}" iv="${SAMPLE_INTERVAL:-30}" i
  for i in $(seq 0 "$((n-1))"); do
    ssh_run "${base_id}-t${i}" "$category" L2 "$cmd"
    [ "$((i+1))" -lt "$n" ] && sleep "$iv"
  done
}
```

The workflow coordinates CPU, memory and I/O series in the same time window.
It may run the three measurements in parallel, with at most three commands, but
must not start another series for the same metric or repeat fresh snapshots.

---

## MODULE:helpers.evidence_reuse

Before execution, check records in `{{RUN_DIR}}/evidencia/`. Reuse within the same
run only when target, normalized payload, parameters and privileges match.
The first topologically ordered skill owns the command; later consumers store
`evidence_refs` instead of rerunning it. Do not reuse across runs by default.

---

## MODULE:helpers.finding

Emit a structured finding to the findings directory.

```bash
emit_finding() {
  local id="$1" title="$2" cat="$3" sev="$4" conf="$5" obs="$6" ev="$7" an="$8" rec="$9" val="${10}" rb="${11}"
  cat >> "{{RUN_DIR}}/findings/findings.md" <<EOF
## $id
- Title: $title
- Category: $cat
- Severity: $sev
- Confidence: $conf
- Observation: $obs
- Evidence: $ev
- Analysis: $an
- Recommendation: $rec
- Validation: $val
- Rollback: $rb
EOF
}
```

---

## MODULE:helpers.safety_guard

Before executing any command that is not clearly read-only: STOP -> ANALYZE -> ASK.

```
Commands prohibited during the read-only phase:
  apt/dpkg/yum/dnf/pacman -i/-r/-u, pip/npm install,
  systemctl start/stop/restart/enable/disable,
  sysctl -w, iptables/firewalld --add/--remove,
  docker restart/stop/rm/prune, kubectl apply/delete/edit,
  rm, chmod/chown, mount/umount, mkfs, dd, reboot/halt,
  kill/pkill, sed -i on configuration files,
  any > >> redirection to /etc /var /root /opt
  outside the evidence directory.

If a mutating command is encountered: do not execute it. Record it as a recommendation.
```
