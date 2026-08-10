# Severity Matrix

## Severity levels

| Level      | Label    | Criteria                                                                     |
|------------|----------|------------------------------------------------------------------------------|
| CRITICAL   | CRIT     | Immediate risk of data loss, outage, or security breach already affecting live traffic. |
| HIGH       | HIGH     | Significant reliability/security gap that will cause an incident if not addressed. |
| MEDIUM     | MEDIUM   | Best-practice gap, configuration hardening opportunity, or forward-looking risk. |
| LOW        | LOW      | Cosmetic, informational improvement, or very low likelihood impact.          |
| INFO       | INFO     | Facts worth noting for operators; no risk per se.                           |

## Confidence levels

| Level   | Criteria                                                     |
|---------|--------------------------------------------------------------|
| HIGH    | Evidence directly proves the claim; verified by test.        |
| MEDIUM  | Evidence supports the claim; one source, no verification.    |
| LOW     | Reasonable inference from indirect evidence or documentation.|

## Rating guidance (avoid false positives)

Before assigning severity, validate all five:

1. **Evidence** — is there a stored evidence YAML? (if not, it's NOT a finding)
2. **Context** — what does this port/process/config DO? Is it INTENDED?
3. **Configuration** — is there authentication, rate limiting, allowlisting?
4. **Exposure** — is it reachable externally? which network boundary? (localhost vs 0.0.0.0 vs internet)
5. **Impact** — if exploited/misconfigured/down, what breaks? which service/data/outage?

## Priority quadrant

```
                  HIGH impact
                      |
    MEDIUM          CRITICAL          <- fix now
     (fix soon)     (fix now)
        |               |
LOW -----------------+--- HIGH likelihood
     (backlog)        HIGH
                      (fix next release)
                      |
                  LOW impact
```

## Capacity status (resource analysis)

| Status   | Criteria                                     |
|----------|----------------------------------------------|
| NORMAL   | Consumption within expected stable range.    |
| WATCH    | Monitor closely, no immediate action needed. |
| WARNING  | Approaching limit or negative trend.         |
| CRITICAL | At or beyond limit, immediate action needed. |
