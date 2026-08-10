# Optimization Comparison — {{HOSTNAME}}

**Baseline:** {{BASELINE_DATE}} (`{{RUN_DIR_A}}`)
**Post-optimization:** {{POST_DATE}} (`{{RUN_DIR_B}}`)
**Cambios aplicados:** {{CHANGES_SUMMARY}}

---

## Resumen ejecutivo

| Axis | Baseline | Post | Delta | Estado |
|------|----------|------|-------|--------|
| CPU (load/nproc) | {{CPU_A}} | {{CPU_B}} | {{CPU_D}} | {{CPU_STATUS}} |
| Memory available % | {{MEM_A}} | {{MEM_B}} | {{MEM_D}} | {{MEM_STATUS}} |
| Swap used % | {{SWAP_A}} | {{SWAP_B}} | {{SWAP_D}} | {{SWAP_STATUS}} |
| Disk uso % | {{DISK_A}} | {{DISK_B}} | {{DISK_D}} | {{DISK_STATUS}} |
| I/O %wait | {{IO_A}} | {{IO_B}} | {{IO_D}} | {{IO_STATUS}} |
| Network retrans % | {{NET_A}} | {{NET_B}} | {{NET_D}} | {{NET_STATUS}} |
| Containers con limits | {{CTR_LIM_A}} | {{CTR_LIM_B}} | {{CTR_LIM_D}} | {{CTR_LIM_STATUS}} |

Leyenda estado: `IMPROVED` · `NO CHANGE` · `REGRESSED` · `NEW ISSUE`

---

## Detalle por recomendacion aplicada

{{#CHANGES}}
### {{ID}} — {{TITLE}}
- **Esperado:** {{EXPECTED}}
- **Medido antes:** {{BEFORE}}
- **Medido despues:** {{AFTER}}
- **Resultado:** {{STATUS}}
- **Notas:** {{NOTES}}
{{/CHANGES}}

---

## Nuevos hallazgos post-optimizacion

{{#NEW_FINDINGS}}
- **{{ID}}** — {{TITLE}} ({{PRIORITY}})
{{/NEW_FINDINGS}}

## Proximos pasos
- Regresiones -> investigar causa y rollback si necesario.
- Sin mejora en metrica esperada -> validar que el cambio se aplico correctamente y volver a medir.
