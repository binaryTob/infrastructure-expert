# Findings Template

Each finding follows this format. Confidence: `HIGH | MEDIUM | LOW | INSUFFICIENT_DATA`.
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
- Command: `...`
- Output (excerpt):
```

```

### Observation (FACT)
What was observed, without interpretation.

### Analysis (INFERENCE)
Why it likely occurs. Cite correlated skills.

### Root Cause (INFERENCE)
Likely cause; if it cannot be established -> `INSUFFICIENT_DATA`.

### Recommendation (RECOMMENDATION)
What to do.

### Expected Benefit
Before: X. Expected after: Y.

### Risk
Risk of applying the recommendation.

### Implementation (not executed by this framework)
Suggested command/configuration.

### Rollback
How to undo the change.

### Validation
How to verify the result (before/after).
