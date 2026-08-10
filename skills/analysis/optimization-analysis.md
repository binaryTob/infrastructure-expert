---
id: "optimization_analysis"
name: "Optimization Analysis"
version: "1.0"
category: "optimization"
phase: "optimize"
risk: "advisory"
execution_mode: "auto"
depends_on: ["capacity_analysis"]
provides: ["optimization_candidates", "ranked_recommendations"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/optimization" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Optimization Analysis

## Objective
Generate prioritized optimization candidates from capacity analysis findings. No changes are applied — recommendations only.

## What it does
This skill does NOT execute new commands. It reads capacity analysis results and all prior evidence to generate a ranked, actionable list of optimization candidates with:
- Area (CPU/MEMORY/DISK/IO/NETWORK/PROCESS/SYSTEMD/DOCKER/KUBERNETES/DATABASE/CONFIGURATION)
- Problem description
- Evidence reference
- Impact (expected benefit)
- Risk of implementation
- Effort (low/medium/high)
- Priority (P0-P4)
- Recommendation (specific, actionable)
- Suggested config/command (read-only suggestion, Level 3)
- Rollback procedure
- Validation method (how to measure before/after)

## Optimization categories
- **CPU**: process limits, scheduler tuning, workload distribution.
- **MEMORY**: swap tuning (vm.swappiness), overcommit (vm.overcommit_memory), container limits.
- **DISK**: fstrim (SSD), filesystem mounts (noatime), log rotation, cleanup.
- **I/O**: ionice for non-critical processes, vm.dirty_ratio tuning, storage tiering.
- **NETWORK**: sysctl tuning (tcp_fastopen, tcp_tw_reuse), connection limits.
- **CONFIGURATION**: sysctl, ulimits, transparent hugepages, service resource limits.
- **DOCKER**: add memory/CPU limits, remove unused images, log rotation.
- **KUBERNETES**: resource requests/limits, QoS, HPA, pod anti-affinity.

## Priority rules
- CRITICAL (P0): risk of data loss, outage, or security breach. Immediate action.
- HIGH (P1): significant reliability/performance gap.
- MEDIUM (P2): best-practice gap, hardening opportunity.
- LOW (P3): cosmetic, informational improvement.
- INFO (P4): observations without risk.

## Output
- `optimization-candidates.yaml` with all candidates.
- `optimization-report.md` for human consumption (see `templates/optimization-report.md`).

## Security
Advisory only. NO commands are applied. Every recommendation includes rollback and validation.
