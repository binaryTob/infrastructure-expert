# Workflow: Incident Triage (symptom -> root cause)

Use when the operator reports a **symptom**, such as "the site returns 502",
"the disk is full" or "a container keeps restarting", rather than requesting a
full audit. The goal is a **root cause** and **remediation**, not a full inventory.

This data-driven workflow reads `lib/diagnosis.yaml` (symptom -> hypotheses ->
evidence -> skills) and runs only the required skills. Adding a symptom is a
change to `diagnosis.yaml`, not hardcoded workflow logic.

## Minimum input

| Variable | Required | Description |
|----------|----------|-------------|
| `SYMPTOM` | yes | Reported symptom, e.g. "502 on app.example.test" |
| `SSH_TARGET` | yes | `user@host` or a configured alias |

## Loop

```text
1. NORMALIZE the symptom -> map it to a diagnosis.yaml ID
     (502 -> http_5xx/502_bad_gateway, cert -> cert_error, etc.)
     |
     v
2. READ diagnosis.yaml: obtain the ordered hypotheses for that ID.
     |
     v
3. FOR EACH hypothesis (in likelihood order):
     - identify required evidence and the skills that produce it
     - reuse existing evidence in reportes/<run-id>/; otherwise run the skill
     - run the non-destructive confirmation check ("confirm")
     - if confirmed -> root cause found; exit
     - if ruled out -> continue to the next hypothesis
     |
     v
4. VERIFY with a second source to reduce false positives:
     evidence + context + exposure + impact (lib/severity.md)
     |
     v
5. GENERATE a finding (FACT/OBSERVATION/HYPOTHESIS/RISK) + severity + confidence
     |
     v
6. GENERATE remediation (WHAT/WHY/HOW/RISK/PRIORITY/VALIDATION/ROLLBACK)
     - if Level 3 is required -> STOP, DOCUMENT, REQUEST APPROVAL
     |
     v
7. REPORT root cause + evidence + remediation (console summary)
```

## Hard rules

1. **Read-only throughout.** Diagnosis never applies fixes automatically. If
   confirmation or remediation requires Level 3, document it and request approval
   (`SAFETY.md`).
2. **Evidence first.** No hypothesis is confirmed without a stored evidence record.
3. **False-positive control.** A hypothesis remains a hypothesis until a
   non-destructive confirmation check validates it. One snapshot is not a trend.
4. **Existing skills first.** Each `how` in `diagnosis.yaml` references existing
   capabilities. Cover missing checks with bounded L1/L2 ad-hoc work; create a
   skill only if it passes the necessity/reuse gate in `WORKFLOW.md`.
5. **Do not assume architecture.** A 502 may come from Apache, nginx or Kubernetes
   ingress; let `web_server_analysis` / `ingress_nginx_analysis` discover it.

## Example: "502 on the site"

```text
symptom -> http_5xx
hypothesis 1: upstream unavailable
  -> run web_server_analysis (proxy map + upstream health)
  -> confirm: curl upstream -> 000 (refused)
  -> verify: docker ps -a + curl container-IP -> no listener
  -> root cause: container 'up' but Rails process terminated (no swap -> OOM)
  -> remediation: restart container + enable swap (Level 3 -> request approval)
```

## Report directory

As with an audit, store evidence in `reportes/<run-id>/evidencia/` and findings in
`reportes/<run-id>/findings.yaml`. Reuse the same `run-id` for an existing run.
