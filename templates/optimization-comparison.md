# Optimization Comparison — {{HOSTNAME}}

**Baseline:** {{BASELINE_DATE}} (`{{RUN_DIR_A}}`)
**Post-optimization:** {{POST_DATE}} (`{{RUN_DIR_B}}`)
**Applied changes:** {{CHANGES_SUMMARY}}

---

## Executive summary

| Axis | Baseline | Post | Delta | Status |
|------|----------|------|-------|--------|
| CPU (load/nproc) | {{CPU_A}} | {{CPU_B}} | {{CPU_D}} | {{CPU_STATUS}} |
| Memory available % | {{MEM_A}} | {{MEM_B}} | {{MEM_D}} | {{MEM_STATUS}} |
| Swap used % | {{SWAP_A}} | {{SWAP_B}} | {{SWAP_D}} | {{SWAP_STATUS}} |
| Disk usage % | {{DISK_A}} | {{DISK_B}} | {{DISK_D}} | {{DISK_STATUS}} |
| I/O %wait | {{IO_A}} | {{IO_B}} | {{IO_D}} | {{IO_STATUS}} |
| Network retrans % | {{NET_A}} | {{NET_B}} | {{NET_D}} | {{NET_STATUS}} |
| Containers with limits | {{CTR_LIM_A}} | {{CTR_LIM_B}} | {{CTR_LIM_D}} | {{CTR_LIM_STATUS}} |

Status legend: `IMPROVED` · `NO CHANGE` · `REGRESSED` · `NEW ISSUE`

---

## Applied recommendation details

{{#CHANGES}}
### {{ID}} — {{TITLE}}
- **Expected:** {{EXPECTED}}
- **Measured before:** {{BEFORE}}
- **Measured after:** {{AFTER}}
- **Result:** {{STATUS}}
- **Notes:** {{NOTES}}
{{/CHANGES}}

---

## New post-optimization findings

{{#NEW_FINDINGS}}
- **{{ID}}** — {{TITLE}} ({{PRIORITY}})
{{/NEW_FINDINGS}}

## Next steps
- Regressions -> investigate the cause and roll back if necessary.
- No improvement in the expected metric -> verify that the change was applied correctly and measure again.
