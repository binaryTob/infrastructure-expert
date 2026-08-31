# Workflow: Advanced Credential Theft Investigation v2.0

Workflow forense avanzado para determinar CÓMO se robaron las .env o las claves
para push de GitHub. Combina skills existentes con un skill nuevo y mejorado
que realiza análisis completo de vectores de ataque.

## Objetivo
Reconstruir el vector de ataque completo:
1. Cómo entró el atacante
2. Qué credenciales accedió
3. Cómo exfiltró los datos
4. Si dejó mecanismos de persistencia

## Diagrama de ejecución

```
PHASE 1: DISCOVERY (existing skills)
  │
  ├── system_inventory        → OS, kernel, users, services, network
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
PHASE 3: ADVANCED CREDENTIAL THEFT INVESTIGATION (NEW v2.0)
  │
  └── advanced_credential_theft_investigation
      │
      ├── Phase 3.1: Complete .env Discovery
      │   ├── All .env files system-wide
      │   ├── .env files in git repos (tracked secrets)
      │   └── .env with weak permissions
      │
      ├── Phase 3.2: GitHub Token & Git Credential Detection
      │   ├── GitHub token patterns in ALL files
      │   ├── .git-credentials and .netrc check
      │   ├── SSH keys audit (for git push)
      │   └── Bash history with tokens/credentials
      │
      ├── Phase 3.3: Docker Secrets Exposure
      │   ├── Container environment variables with secrets
      │   └── Docker socket exposure
      │
      ├── Phase 3.4: Web Exposure Analysis
      │   ├── HTTP probes for .env files
      │   └── Exposed git repositories via HTTP
      │
      ├── Phase 3.5: Filesystem Forensics
      │   ├── Recently modified credential files
      │   ├── Processes with credential files open
      │   └── Deleted files still open
      │
      ├── Phase 3.6: Audit Log Analysis
      │   ├── Authentication events
      │   └── Post-exploitation indicators
      │
      ├── Phase 3.7: Network Exfiltration Detection
      │   ├── Outbound connections
      │   └── Cron jobs with network commands
      │
      └── Phase 3.8: Attack Vector Correlation
          └── Timeline reconstruction
  │
  v
PHASE 4: PLATFORM (existing conditional skills)
  │
  ├── docker_analysis         → container inventory (if Docker present)
  ├── web_server_analysis     → nginx/apache config (if web server present)
  ├── tls_certificate_analysis→ cert audit (if web server present)
  ├── database_analysis       → DB connections, config (if DB present)
  └── log_analysis            → journal errors, OOM, disk errors
  │
  v
PHASE 5: RESOURCES (existing skills)
  │
  ├── cpu_analysis
  ├── memory_analysis
  ├── disk_analysis
  └── io_analysis
  │
  v
PHASE 6: ANALYSIS & CORRELATION (existing skills)
  │
  ├── configuration_analysis  → sysctl, limits, server config
  ├── reliability_analysis    → SPOF, restart policies
  └── observability_analysis  → monitoring, log rotation
  │
  v
PHASE 7: FINDINGS GENERATION
  │
  ├── Cross-reference all evidence from Phase 3
  ├── Build attack timeline hypothesis
  ├── Determine root cause (initial access vector)
  ├── Generate findings with severity + confidence
  └── Write findings.yaml
  │
  v
PHASE 8: REPORT
  │
  ├── Generate forensic HTML report
  └── Print executive summary with:
      ├── Attack vector hypothesis
      ├── Credentials compromised
      ├── Exfiltration method
      └── Recommended remediations
```

## Reglas de ejecución por fase

### Fase 1-2 (Discovery + Security Base)
- Ejecutar TODOS los skills sin condicionales
- Son la base del inventario y postura de seguridad

### Fase 3 (Advanced Credential Theft Investigation)
- Ejecutar EL skill `advanced_credential_theft_investigation`
- Este skill es autocontenido y ejecuta todas las fases internas
- NO requiere skills adicionales (pero puede complementarlos)

### Fase 4 (Platform)
- Ejecutar SOLO si el componente fue detectado en Fase 1
- Seguir triggers de `_index.yaml`

### Fase 5-6 (Resources + Analysis)
- Ejecutar todos — son cheap y provide contexto

## Reglas duras

1. **Read-only.** Nada que modifique el servidor.
2. **Evidence first.** Cada afirmación con evidencia almacenada.
3. **Fact vs Hypothesis.** Etiquetar cada claim.
4. **Secret redaction.** Valores nunca en evidencia/reporte.
5. **No assumptions.** Descubrir, nunca asumir.

## Output

Directorio de reportes: `reportes/<run-id>/`
- `reportes/<run-id>/evidencia/` — YAML records por comando
- `reportes/<run-id>/advanced-credential-theft/` — evidencia del skill principal
- `reportes/<run-id>/findings/` — hallazgos
- `reportes/<run-id>/findings.yaml` — findings estructurados
- `reportes/<run-id>/inventory.yaml` — inventario
- `reportes/<run-id>/informe-forense-<run-id>.html` — reporte HTML forense

## Safety levels

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
