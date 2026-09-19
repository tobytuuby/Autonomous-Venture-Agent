# Autonomous Venture Agent — Phase 3 Implementation Plan

## v1.2 — P3.2

**Status:** P3.2 active; acceptance review pending
**Predecessor:** phase3-implementation-plan-v1.1.md
**Execution class:** Synthetic integration and shadow reasoning only

## Scope

P3.2 consumes P3.1 normalized intake records and produces deterministic shadow
Voyage Candidates. It records lifecycle transitions, requires human review for
acceptance, and preserves frozen weight and reasoning snapshots.

## Deliverables

- kernel/scout/scoring.py
- schemas/p3/scoring-weight-set.schema.json
- schemas/p3/voyage-candidate.schema.json
- schemas/p3/lifecycle-transition.schema.json
- schemas/p3/review-decision.schema.json
- tests/p3/test_p3_2_scoring.py and P3.2 fixtures
- docs/adr/ADR-P3-003-scoring-lifecycle.md
- tests/certification/p3-raw/P3-2.json and P3.2 evidence manifest

No migration is introduced. P3.2 uses a separate synthetic SQLite store and
does not write to P2 or P3.1 state.

## Frozen policy

Weight version: p3.2-w1. Threshold: 70. Expiration window: 30 days by
default. Repeated quarantine escalates on the second quarantine. Weight
updates are rejected; a future change requires a new version.

## Denominator and evidence

P3.2 has a separate denominator. It is not merged into P2's 41 tests,
P3.0's 6 tests, P3.1's 13 tests, or the P0/P1 ADV denominator. Reasoning
chains, weight snapshots, lifecycle transitions, human review records,
quarantine reasons, and raw test output are retained.

## Exit conditions

- deterministic scores and confidence intervals are reproduced;
- poor fit, low confidence, contradiction, expiration, and escalation cases
  are denied or quarantined as specified;
- only a human operator can accept a candidate;
- all lifecycle audit transitions reconstruct;
- no capital, venture, worker, payment, credential, broker, deployment,
  customer, or external action path exists;
- analyst/auditor review records the decision and limitations.
