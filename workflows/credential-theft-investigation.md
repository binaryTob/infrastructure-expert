# Workflow: Credential Theft Investigation

Investigación forense de robo de credenciales (.env / GitHub push keys).
Ejecuta skills existentes + 7 skills forenses nuevos para reconstruir el vector de ataque.

## Entrada mínima

| Variable | Requerido | Default | Descripción |
|----------|-----------|---------|-------------|
| `SSH_TARGET` | si | — | `user@host` o alias SSH configurado |
| `MODE` | no | `forensic` | `forensic` (default para este workflow) |

## Diagrama de ejecución

```
PHASE 1: DISCOVERY (existing skills)
  │
  ├── system_inventory        → OS, kernel, users, services, network triage
  ├── systemd_analysis        → services, timers, restarts
  ├── process_analysis        → all processes, tree, zombies
  └── network_analysis        → interfaces, ports, connections, firewall
  │
  v
PHASE 2: SECURITY BASELINE (existing skills)
  │
  ├── security_analysis       → SSH posture, privileged procs, persistence
  └── ssh_hardening_analysis  → sshd_config, fail2ban, authorized_keys
  │
  v
PHASE 3: CREDENTIAL EXPOSURE (NEW forensic skills)
  │
  ├── credential_exposure_analysis  → ALL .env files, permissions, web exposure
  ├── git_credential_analysis       → .git-credentials, .git/config tokens, SSH keys
  └── docker_secrets_analysis       → container env vars, mounts, privileged (conditional)
  │
  v
PHASE 4: FORENSIC TIMELINE (NEW forensic skills)
  │
  ├── filesystem_forensics    → file access timeline, open files, deleted artifacts
  └── audit_logs_forensics    → auth logs, auditd, post-exploitation indicators
  │
  v
PHASE 5: ATTACK SURFACE (NEW forensic skills)
  │
  ├── web_secret_exposure     → HTTP probes for .env, config files, phpinfo (conditional)
  └── network_exfiltration    → outbound connections, curl in cron, SSH tunnels
  │
  v
PHASE 6: PLATFORM (existing conditional skills)
  │
  ├── docker_analysis         → container inventory (if Docker present)
  ├── web_server_analysis     → nginx/apache config (if web server present)
  ├── tls_certificate_analysis→ cert audit (if web server present)
  ├── database_analysis       → DB connections, config (if DB present)
  └── log_analysis            → journal errors, OOM, disk errors
  │
  v
PHASE 7: RESOURCES (existing skills)
  │
  ├── cpu_analysis
  ├── memory_analysis
  ├── disk_analysis
  └── io_analysis
  │
  v
PHASE 8: ANALYSIS & CORRELATION (existing skills)
  │
  ├── configuration_analysis  → sysctl, limits, server config
  ├── reliability_analysis    → SPOF, restart policies
  └── observability_analysis  → monitoring, log rotation
  │
  v
PHASE 9: FINDINGS GENERATION
  │
  ├── Cross-reference all evidence
  ├── Build attack timeline hypothesis
  ├── Generate findings with severity + confidence
  └── Write findings.yaml
  │
  v
PHASE 10: REPORT
  │
  ├── Generate forensic HTML report
  └── Print executive summary
```

## Reglas de ejecución por fase

### Fase 1-2 (Discovery + Security Base)
- Ejecutar TODOS los skills sin condicionales
- Son la base del inventario y postura de seguridad

### Fase 3-5 (Forensic Skills — NUEVOS)
- Ejecutar TODOS los skills forenses
- `docker_secrets_analysis`: solo si Docker está presente (trigger automático)
- `web_secret_exposure`: solo si hay servidor web (trigger automático)
- Los demás se ejecutan siempre

### Fase 6 (Platform)
- Ejecutar SOLO si el componente fue detectado en Fase 1
- Seguir triggers de `_index.yaml`

### Fase 7-8 (Resources + Analysis)
- Ejecutar todos — son cheap y provide contexto

## Reglas duras (heredadas de infrastructure-audit.md)

1. **Read-only.** Nada que modifique el servidor.
2. **Evidence first.** Cada afirmación con evidencia almacenada.
3. **Fact vs Hypothesis.** Etiquetar cada claim.
4. **Secret redaction.** Valores nunca en evidencia/reporte.
5. **No assumptions.** Descubrir, nunca asumir.

## Output

Directorio de reportes: `reportes/<run-id>/`
- `reportes/<run-id>/evidencia/` — YAML records por comando
- `reportes/<run-id>/findings/` — hallazgos
- `reportes/<run-id>/findings.yaml` — findings estructurados
- `reportes/<run-id>/inventory.yaml` — inventario
- `reportes/<run-id>/informe-forense-<run-id>.html` — reporte HTML forense

## Safety levels (ver SAFETY.md)

| Level | Name | Scope | Default |
|-------|------|-------|---------|
| 1 | OBSERVE | Read-only commands | Always on |
| 2 | TEST | Non-destructive tests (HTTP probes) | On by default |
| 3 | CHANGE | Mutating actions | Off — requires explicit approval |

## Creación dinámica de skills

Si se detecta una tecnología sin skill correspondiente durante la investigación:
1. Identificar la tecnología.
2. Crear `skills/<area>/<tech>/SKILL.md` según `_template.md`.
3. Validar contra `_schema.yaml`.
4. Ejecutar (L1/L2 solamente).
5. Persistir para reuso.
