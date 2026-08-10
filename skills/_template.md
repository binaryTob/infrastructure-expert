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
  OUTPUT_DIR:
    type: "filepath"
    default: "{{RUN_DIR}}/{{SKILL_ID}}"
    description: "Directorio de evidencia para esta skill"
  SSH_TARGET:
    type: "string"
    required: true
    description: "Espec SSH: user@host o alias configurado"
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
| `{{OUTPUT_DIR}}` | filepath | si | auto | Directorio de evidencia |
| `{{SSH_TARGET}}` | string | si | — | Espec SSH |
| `{{SAMPLE_INTERVAL}}` | duration | no | 30s | Intervalo de snapshot |
| `{{SAMPLE_COUNT}}` | integer | no | 4 | Nro de snapshots |

## Pre-flight (validacion de entorno, read-only)
```bash
# [risk:info] [mode:auto]
for c in <TOOL_LIST>; do command -v "$c" >/dev/null 2>&1 && echo "OK $c" || echo "MISSING $c"; done
```

## Comandos

### 1. Snapshot T0
```bash
# [risk:ro] [mode:auto]
ssh "{{SSH_TARGET}}" '<COMANDO_READ_ONLY>' | tee "{{OUTPUT_DIR}}/t0-metrica.txt"
```

### 2. Serie temporal (T+30s ... T+N)
```bash
# [risk:probe] [mode:auto]
for i in $(seq 1 {{SAMPLE_COUNT}}); do
  ssh "{{SSH_TARGET}}" '<COMANDO>' | tee "{{OUTPUT_DIR}}/t${i}-metrica.txt"
  sleep {{SAMPLE_INTERVAL}}
done
```

### 3. Bloque condicional (si componente presente)
```bash
# [risk:ro] [mode:auto] [requires:COMPONENT_DETECTED]
ssh "{{SSH_TARGET}}" '<COMANDO>' | tee "{{OUTPUT_DIR}}/componente.txt"
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
- `metrica.txt` / `metrica.json` en `{{OUTPUT_DIR}}`

## Seguridad
Todos los bloques son read-only. Si aparece algo sospechoso (miner, proceso desconocido): FLAG + COLLECT + REPORT, no modificar.

## Referencias
- doc / URL
