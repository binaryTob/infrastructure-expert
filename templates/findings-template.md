# Findings Template

Cada finding sigue este formato. Confidence: `HIGH | MEDIUM | LOW | INSUFFICIENT_DATA`.
Severity: `P0 | P1 | P2 | P3 | P4`.

---

## FINDING-NNN

### Title
...

### Category
CPU / MEMORY / DISK / IO / NETWORK / PROCESS / SYSTEMD / DOCKER / KUBERNETES / DATABASE / LOGGING / SECURITY / CONFIGURATION / CAPACITY / BACKUP / RELIABILITY / OBSERVABILITY / MIGRATION

### Severity
P0 / P1 / P2 / P3 / P4

### Confidence
HIGH / MEDIUM / LOW / INSUFFICIENT_DATA

### Evidence (FACT)
- Comando: `...`
- Output (extracto): ```

```

### Observation (FACT)
Que se observo, sin interpretacion.

### Analysis (INFERENCE)
Por que probablemente ocurre. Citar skills correlacionadas.

### Root Cause (INFERENCE)
Causa probable; si no se puede afirmar -> `INSUFFICIENT_DATA`.

### Recommendation (RECOMMENDATION)
Que hacer.

### Expected Benefit
Antes: X. Despues esperado: Y.

### Risk
Riesgo de aplicar la recomendacion.

### Implementation (no ejecutado en este framework)
Comando/config sugerido.

### Rollback
Como deshacer el cambio.

### Validation
Como comprobar que funciono (antes/despues).
