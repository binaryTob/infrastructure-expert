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
9. **Reusar evidencia.** Una skill consume evidencia fresca de sus dependencias; no repite comandos para obtener la misma vista.
10. **Diagnostico bajo demanda.** La presencia de una tecnologia habilita postura/inventario, no troubleshooting, logs profundos ni forense sin sintoma o anomalia.
11. **Skills excepcionales.** Tecnologia sin soporte -> skill generica o check ad-hoc acotado. Solo persistir una skill si supera el gate completo de `WORKFLOW.md`.
12. **Concurrencia acotada.** Maximo 3 comandos L1 livianos e independientes; serializar scans globales, logs, DB, dumps de cluster y pruebas del mismo subsistema.

## Modos

| Modo | Seleccion | Descripcion |
|------|-----------|-------------|
| `full` | candidatos de `_index.yaml` + triggers | Analisis completo, condicionado por evidencia |
| `quick` | conjunto minimo + dependencias | Triage rapido |
| `discovery` | inventario, systemd, procesos, red | Solo descubrimiento e inventario |
| `container` | candidatos Docker/K8s + dependencias | Host de contenedores; diagnostico solo ante anomalías |
| `security` | postura de seguridad + dependencias | Auditoria de seguridad |
| `forensic` | candidatos forenses + dependencias | Solo con objetivo/indicadores forenses explicitos |

Los conteos no se hardcodean: se derivan del catalogo y pueden cambiar. La secuencia del modo es un conjunto candidato; el agente agrega dependencias, ordena topologicamente y aplica triggers antes de ejecutar.

## Directorio de reportes

Toda la evidencia y reportes se guardan en `reportes/<run-id>/`:
- `reportes/<run-id>/evidencia/` — registros YAML por comando
- `reportes/<run-id>/findings/` — hallazgos
- `reportes/<run-id>/inventory.yaml` — inventario
- `reportes/<run-id>/graph.yaml` — grafo de infraestructura
- `reportes/<run-id>/informe-<run-id>.html` — reporte HTML offline

## Tecnologia sin skill

No crear una skill por presencia de producto. Registrar la tecnologia en inventario, reutilizar skills genericas y, si queda una pregunta concreta, ejecutar un check ad-hoc L1/L2 acotado mediante `scripts/ssh_exec.sh`.

Persistir una skill solo cuando sea necesaria para el objetivo actual, reutilizable entre hosts/runs, no se solape con capacidades existentes, use interfaces estables, minimice comandos y supere validacion + ejecucion. Ver el gate vinculante en `WORKFLOW.md`.

## Safety levels (ver SAFETY.md)

| Level | Name | Scope | Default |
|-------|------|-------|---------|
| 1 | OBSERVE | Read-only commands | Always on |
| 2 | TEST | Non-destructive tests | On by default |
| 3 | CHANGE | Mutating actions | Off — requires explicit approval |
