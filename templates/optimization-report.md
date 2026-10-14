# Optimization Report — {{HOSTNAME}}

**Date:** {{DATE}} · **Server:** {{SERVER_NAME}} · **Read-only / advisory**

> No changes were applied. Listed configurations/commands are **suggestions**.
> Each recommendation includes validation and rollback.

---

## Summary table

| ID | Area | Problem | Evidence | Impact | Risk | Effort | Priority |
| -- | ---- | -------- | --------- | ------- | ------ | -------- | --------- |
{{#OPTIMIZATION_ROWS}}
| {{ID}} | {{AREA}} | {{PROBLEM}} | {{EVIDENCE_SHORT}} | {{IMPACT}} | {{RISK}} | {{EFFORT}} | {{PRIORITY}} |
{{/OPTIMIZATION_ROWS}}

---

## Recommendation details

{{#OPTIMIZATION_ITEMS}}
### {{ID}} — {{TITLE}}
- **Category:** {{CATEGORY}}  ·  **Priority:** {{PRIORITY}}  ·  **Risk:** {{RISK}}  ·  **Effort:** {{EFFORT}}  ·  **Confidence:** {{CONFIDENCE}}

**Problem**
{{PROBLEM}}

**Evidence**
```
{{EVIDENCE}}
```

**Expected impact**
{{IMPACT}}

**Recommendation**
{{RECOMMENDATION}}

**Suggested configuration / command (not executed)**
```
{{CONFIG_SUGGESTED}}
```

**Rollback**
{{ROLLBACK}}

**Validation (before -> after)**
- Before:  {{BEFORE_METRIC}}
- Change:  {{CHANGE}}
- Expected after:  {{AFTER_METRIC}}
- How to measure:  {{VALIDATION_CMD}}

---
{{/OPTIMIZATION_ITEMS}}

## Next steps
1. Address P0 (CRITICAL) recommendations first, followed by P1.
2. Rerun analysis (POST-OPTIMIZATION phase) and compare.
3. Generate `optimization-comparison.md`.
