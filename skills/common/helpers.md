# Common Helpers — Infrastructure Expert

Modulos reutilizables inyectables en skills/workflow mediante `<!-- MODULE:helpers.nombre -->`.
Ejecucion **read-only** sobre SSH. Nada instala, reinicia ni modifica nada en el servidor.

---

## MODULE:helpers.ssh_run

Unico punto de entrada para comandos remotos. Delega captura y redaccion al wrapper
canonico; ninguna skill implementa su propio SSH ni escribe salida remota directamente.

```bash
# Uso: ssh_run <evidence-id> <category> <L1|L2> <remote-command>
ssh_run() {
  local evidence_id="$1" category="$2" level="$3" cmd="$4"
  scripts/ssh_exec.sh "$evidence_id" "$category" "$level" "$cmd" "{{RUN_DIR}}/evidencia"
}
```

---

## MODULE:helpers.redact

La redaccion esta centralizada en `scripts/redact.py` y es invocada por
`scripts/ssh_exec.sh` antes de persistir evidencia. No duplicar expresiones regulares
en skills: las implementaciones parciales divergen y pueden filtrar secretos.

---

## MODULE:helpers.detect

Deteccion dinamica de componentes presentes en el host (read-only).
El workflow usa esto para decidir que skills ejecutar y cuales SKIPear.

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

Loop de snapshots temporales SIN carga artificial (solo `sleep` + medicion).

```bash
snapshot_loop() {
  local base_id="$1" category="$2" cmd="$3" n="${SAMPLE_COUNT:-4}" iv="${SAMPLE_INTERVAL:-30}" i
  for i in $(seq 0 "$((n-1))"); do
    ssh_run "${base_id}-t${i}" "$category" L2 "$cmd"
    [ "$((i+1))" -lt "$n" ] && sleep "$iv"
  done
}
```

El workflow coordina las series de CPU, memoria e I/O en una misma ventana temporal.
Puede ejecutar las tres mediciones en paralelo, con maximo 3 comandos, pero nunca
iniciar otra serie de la misma metrica ni repetir snapshots ya frescos.

---

## MODULE:helpers.evidence_reuse

Antes de ejecutar, consultar los registros en `{{RUN_DIR}}/evidencia/`. Reusar dentro
del mismo run solo si coinciden target, payload normalizado, parametros y privilegio.
El primer skill topologicamente ordenado es owner del comando; consumidores posteriores
guardan `evidence_refs`, no vuelven a ejecutarlo. No reutilizar entre runs por defecto.

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
