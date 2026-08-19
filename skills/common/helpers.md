# Common Helpers — Infrastructure Expert

Modulos reutilizables inyectables en skills/workflow mediante `<!-- MODULE:helpers.nombre -->`.
Ejecucion **read-only** sobre SSH. Nada instala, reinicia ni modifica nada en el servidor.

---

## MODULE:helpers.ssh_run

Ejecuta un comando remoto y registra evidencia con `timestamp | host | command | exit_code | output`.
No guarda secretos; pasa la salida por `helpers.redact` antes de escribir.

```bash
# Uso: ssh_run "<evidence-path>" "<remote-command>"
ssh_run() {
  local out="$1" cmd="$2" ts host ec body
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  host="$(ssh -o BatchMode=yes {{SSH_TARGET}} 'hostname -s' 2>/dev/null || echo unknown)"
  ec=0
  body="$(ssh -o BatchMode=yes {{SSH_TARGET}} "$cmd" 2>&1)" || ec=$?
  {
    echo "Timestamp: $ts"
    echo "Host: $host"
    echo "Command: $cmd"
    echo "Exit code: $ec"
    echo
    printf '%s\n' "$body"
    echo "----"
  } >> "$out"
  printf '%s\n' "$body"
}
```

---

## MODULE:helpers.redact

Redacta datos sensibles de la evidencia ANTES de escribir a disco.

```bash
redact() {
  sed -E \
    -e 's/(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)["\x27 :=]+[^\n]*/\1=[REDACTED]/Ig' \
    -e 's/(-----BEGIN [A-Z ]*PRIVATE KEY-----)([\s\S]*?)(-----END [A-Z ]*PRIVATE KEY-----)/\1 [REDACTED] \3/Ig' \
    -e 's#(postgres|mysql|mongodb|redis)(://[^:@/]+:)[^@]+@#\1\2[REDACTED]@#gI' \
    -e 's/(Bearer|Basic) [A-Za-z0-9._\-]+/\1 [REDACTED]/Ig'
}
```

---

## MODULE:helpers.detect

Deteccion dinamica de componentes presentes en el host (read-only).
El workflow usa esto para decidir que skills ejecutar y cuales SKIPear.

```bash
detect_components() {
  ssh -o BatchMode=yes {{SSH_TARGET}} 'for c in systemctl docker docker-compose kubectl helm crictl \
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
    grep -rliE "adapter: (postgresql|mysql|mysql2)|DATABASE_URL" /opt /home /root /srv /app --include="*.yml" --include="*.yaml" --include=".env*" 2>/dev/null | head -1 | grep -q . && echo "PRESENT:db_config"
    [ -f /etc/os-release ] && . /etc/os-release && echo "OS:${PRETTY_NAME:-unknown}"
    systemd-detect-virt 2>/dev/null || true'
}
```

---

## MODULE:helpers.snapshot_loop

Loop de snapshots temporales SIN carga artificial (solo `sleep` + medicion).

```bash
snapshot_loop() {
  local cmd="$1" outdir="$2" n="${SAMPLE_COUNT:-4}" iv="${SAMPLE_INTERVAL:-30}" i
  for i in $(seq 0 "$((n-1))"); do
    ssh_run "${outdir}/t${i}.txt" "$cmd"
    [ "$((i+1))" -lt "$n" ] && sleep "$iv"
  done
}
```

---

## MODULE:helpers.finding

Emite un finding estructurado al directorio de hallazgos.

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

Antes de ejecutar cualquier comando que no sea claramente read-only: STOP -> ANALYZE -> ASK.

```
Comandos prohibidos en fase read-only:
  apt/dpkg/yum/dnf/pacman -i/-r/-u, pip/npm install,
  systemctl start/stop/restart/enable/disable,
  sysctl -w, iptables/firewalld --add/--remove,
  docker restart/stop/rm/prune, kubectl apply/delete/edit,
  rm, chmod/chown, mount/umount, mkfs, dd, reboot/halt,
  kill/pkill, sed -i sobre configs,
  cualquier redireccion > >> hacia /etc /var /root /opt
  fuera del directorio de evidencia.

Si aparece un comando de modificacion: NO ejecutar. Registrar como recomendacion.
```
