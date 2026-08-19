# Workflow: Infrastructure Audit

Flujo principal de analisis de infraestructura. Read-only, reusable contra cualquier servidor Linux accesible por SSH.
La IA lee `skills/_index.yaml` y este documento para orquestar la ejecucion.

## Entrada minima

| Variable | Requerido | Default | Descripcion |
|----------|-----------|---------|-------------|
| `SSH_TARGET` | si | — | `user@host` o alias SSH configurado (`~/.ssh/config`) |
| `MODE` | no | `full` | `full` / `quick` / `discovery` / `container` / `security` |

## Diagrama de ejecucion

```
CONNECT (verificar SSH, sin asumir OS)
  |
  v
DISCOVER (skills/discovery — amplio, barato, read-only)
  |
  v
CLASSIFY -> BUILD INVENTORY -> BUILD GRAPH
  |
  v
DETECT COMPONENTS -> SELECT SKILLS (solo los que aplican)
  |
  v
RUN ANALYSIS (skills seleccionados, tests no destructivos)
  |
  v
FIND ANOMALIES -> CREATE HYPOTHESES -> TEST -> VERIFY
  |
  v
GENERATE FINDINGS + REMEDIATIONS
  |
  v
[si migration] MIGRATION ANALYSIS
  |
  v
GENERATE REPORT -> PRINT EXECUTIVE SUMMARY
```

## Reglas duras

1. **Read-only.** Si un comando no es claramente `ro|info|probe` -> STOP -> registrar como recomendacion, no ejecutar.
2. **Deteccion dinamica.** Ejecutar skills condicionales solo si su `trigger` se cumple. Si no -> SKIP.
3. **Sin asunciones.** Distribucion, init system, container runtime, orquestador, ingress, databases, WAF, firewall, cloud provider: todo debe ser *descubierto*, nunca asumido.
4. **Evidencia primero.** Ninguna afirmacion sobre el servidor sin un registro de evidencia almacenado.
5. **Hecho vs Hipotesis.** Etiquetar cada afirmacion como `FACT`, `OBSERVATION`, `HYPOTHESIS`, `RISK`, o `RECOMMENDATION`.
6. **Redaccion de secretos.** Los secretos se *detectan y reportan como metadata* (ubicacion, tipo, riesgo). Los valores se redactan antes de cualquier salida.
7. **No hardcodear servidores.** Cero `if hostname==`. Toda decision por deteccion de componentes.
8. **Anti-falsos-positivos.** 1 snapshot no es tendencia. Usar `SAMPLE_COUNT >= 4` para inferencias.

## Modos

| Modo | Skills | Descripcion |
|------|--------|-------------|
| `full` | 27 skills | Analisis completo |
| `quick` | 13 skills | Triage rapido |
| `discovery` | 4 skills | Solo descubrimiento e inventario |
| `container` | 13 skills | Host de contenedores |
| `security` | 7 skills | Auditoria de seguridad |

## Directorio de reportes

Toda la evidencia y reportes se guardan en `reportes/<run-id>/`:
- `reportes/<run-id>/evidencia/` — registros YAML por comando
- `reportes/<run-id>/findings/` — hallazgos
- `reportes/<run-id>/inventory.yaml` — inventario
- `reportes/<run-id>/graph.yaml` — grafo de infraestructura
- `reportes/<run-id>/informe-<run-id>.html` — reporte HTML offline

## Dynamic skill generation

Si se detecta una tecnologia sin skill correspondiente:
1. Identificar la tecnologia (binario, version, config path, units).
2. Crear `skills/<area>/<tech>/SKILL.md` segun el schema de `_template.md`.
3. Validar schema contra `_schema.yaml`.
4. Ejecutar (L1/L2 solamente), capturar evidencia.
5. Persistir el `SKILL.md` para reuso.

## Safety levels (ver SAFETY.md)

| Level | Name | Scope | Default |
|-------|------|-------|---------|
| 1 | OBSERVE | Read-only commands | Always on |
| 2 | TEST | Non-destructive tests | On by default |
| 3 | CHANGE | Mutating actions | Off — requires explicit approval |
