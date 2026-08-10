# Optimization Report — {{HOSTNAME}}

**Fecha:** {{DATE}} · **Server:** {{SERVER_NAME}} · **Read-only / advisory**

> Ningun cambio fue aplicado. Las configuraciones/comandos listados son **sugerencias**.
> Cada recomendacion incluye validacion y rollback.

---

## Tabla resumen

| ID | Area | Problema | Evidencia | Impacto | Riesgo | Esfuerzo | Prioridad |
| -- | ---- | -------- | --------- | ------- | ------ | -------- | --------- |
{{#OPTIMIZATION_ROWS}}
| {{ID}} | {{AREA}} | {{PROBLEM}} | {{EVIDENCE_SHORT}} | {{IMPACT}} | {{RISK}} | {{EFFORT}} | {{PRIORITY}} |
{{/OPTIMIZATION_ROWS}}

---

## Detalle por recomendacion

{{#OPTIMIZATION_ITEMS}}
### {{ID}} — {{TITLE}}
- **Categoria:** {{CATEGORY}}  ·  **Prioridad:** {{PRIORITY}}  ·  **Riesgo:** {{RISK}}  ·  **Esfuerzo:** {{EFFORT}}  ·  **Confianza:** {{CONFIDENCE}}

**Problema**
{{PROBLEM}}

**Evidencia**
```
{{EVIDENCE}}
```

**Impacto esperado**
{{IMPACT}}

**Recomendacion**
{{RECOMMENDATION}}

**Configuracion / comando sugerido (no ejecutado)**
```
{{CONFIG_SUGGESTED}}
```

**Rollback**
{{ROLLBACK}}

**Validacion (before -> after)**
- Before:  {{BEFORE_METRIC}}
- Cambio:  {{CHANGE}}
- After esperado:  {{AFTER_METRIC}}
- Como medir:  {{VALIDATION_CMD}}

---
{{/OPTIMIZATION_ITEMS}}

## Proximos pasos
1. Aplicar primero las P0 (CRITICAL) seguidas de P1.
2. Re-ejecutar el analisis (fase POST-OPTIMIZATION) y comparar.
3. Generar `optimization-comparison.md`.
