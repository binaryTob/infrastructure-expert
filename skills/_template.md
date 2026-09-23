---
id: "skill_id"
name: "Skill: Nombre descriptivo"
version: "1.0"
category: "cpu"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: []
provides: []
triggers:
  - "Condicion 1 que activa esta skill"
  - "Condicion 2"
false_positives:
  - "FP 1: descripcion y como descartarlo"
references:
  - "URL / doc de kernel o tuning"
parameters:
  SAMPLE_INTERVAL:
    type: "duration"
    default: "30s"
    required: false
    description: "Intervalo entre snapshots para analisis temporal"
  SAMPLE_COUNT:
    type: "integer"
    default: 4
    required: false
    description: "Cantidad de snapshots (T0, T+30, T+60, T+120...)"
output:
  format: "json"
  schema: "output_schema"
---

# Skill: Nombre descriptivo

## Objetivo
Descripcion concisa (1-2 frases) de que mide y para que esta skill.

## Cuando usarla
- Trigger 1
- Trigger 2

## Parametros

| Variable | Tipo | Requerido | Default | Descripcion |
|----------|------|-----------|---------|-------------|
| `{{SAMPLE_INTERVAL}}` | duration | no | 30s | Intervalo de snapshot |
| `{{SAMPLE_COUNT}}` | integer | no | 4 | Nro de snapshots |

## Pre-flight (validacion de entorno, read-only)
```bash
# [risk:info] [mode:auto]
for c in <TOOL_LIST>; do command -v "$c" >/dev/null 2>&1 && echo "OK $c" || echo "MISSING $c"; done
```

Los bloques describen el payload remoto. El agente los ejecuta exclusivamente con
`scripts/ssh_exec.sh <evidence-id> <category> <L1|L2> <payload> [evidence-dir]`;
no ejecutar los ejemplos con `ssh` directo ni redirigir salida remota sin redaccion.
Las series temporales son la excepcion de orquestacion local: usan
`helpers.snapshot_loop`, que invoca el wrapper una vez por muestra para no exceder timeouts.

## Comandos

### 1. Snapshot T0
```bash
# [risk:ro] [mode:auto]
<COMANDO_READ_ONLY>
```

### 2. Serie temporal (T+30s ... T+N)
```bash
# [risk:probe] [mode:auto]
snapshot_loop "{{SKILL_ID}}-trend" "<category>" '<COMANDO_READ_ONLY>'
```

### 3. Bloque condicional (si componente presente)
```bash
# [risk:ro] [mode:auto] [requires:COMPONENT_DETECTED]
<COMANDO>
```

## Analisis / Interpretacion
- Hallazgo A -> conclusion X
- Hallazgo B -> conclusion Y

## Falsos positivos
- FP 1: descripcion y como descartarlo
- FP 2: descripcion y como descartarlo

## Umbrales (referenciales, ajustar por contexto)
| Metrica | NORMAL | WATCH | WARNING | CRITICAL |
|---------|--------|-------|---------|----------|
| (%)     | < 50   | 50-70 | 70-85   | > 85     |

## Evidencia producida
- `<evidence-id>.yml` en `{{RUN_DIR}}/evidencia/`, generado por `scripts/ssh_exec.sh`

## Seguridad
Todos los bloques son read-only. Si aparece algo sospechoso (miner, proceso desconocido): FLAG + COLLECT + REPORT, no modificar.

## Referencias
- doc / URL
