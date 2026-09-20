# Phase 6 Implementation Plan v1.3 — P6.3 Aggregate Anomaly Controls

Status: adopted for P6.3 planning and implementation; synthetic-only.
Baseline: 387f9138d0e550d4171faa83048eb4532d2b2466 (P6.2 accepted).
Locked configuration fingerprint: 8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11.

## Objective

Detect deterministic aggregate anomalies across synthetic P6.0–P6.2 records without executing, mutating venture state, granting authority, or contacting external systems. Findings must be attributable, replayable, and routed to quarantine or human review.

## Controls

The P6.3 analyzer covers:

- cross-venture leakage;
- slow drift in synthetic demand or quota usage;
- duplicate or structuring-like patterns;
- stale evidence;
- quota exhaustion;
- configuration mismatch;
- unexpected counterparty or beneficiary reuse.

Inputs are immutable synthetic records. The analyzer produces findings only. A finding can require review or quarantine the affected synthetic record; it cannot execute an action or grant capability.

## Boundaries

The analyzer has no provider, network, credential, payment, broker, customer, deployment, capital, venture, or worker execution path. It does not mutate P6.0 registry records, P6.1 coordination records, or P6.2 demand records. Quarantine is an append-only local finding record with reason, evidence hash, scope, and review status.

## Deterministic contract

Every analysis request includes portfolio scope, source record IDs and hashes, policy version, configuration fingerprint, lineage, taint, analysis timestamp, and canonical input hash. The same canonical input produces the same finding hashes and decision. Cross-configuration or cross-venture input mixing fails closed.

## Proposed sub-gates

1. P6.3-A — Anomaly input schema and provenance review.
2. P6.3-B — Detection rules and seeded anomaly fixtures review.
3. P6.3-C — Quarantine/review, replay, and false-positive/negative review.
4. P6.3-D — Evidence readiness and authority-negative review.
5. P6.3 acceptance — focused evidence, full regression, certifications, and explicit human acceptance before P6.4.

## Planned focused denominator

Eighteen scenarios are planned: clean aggregate; cross-venture leakage; slow drift; duplicate pattern; structuring-like pattern; stale evidence; quota exhaustion; configuration mismatch; counterparty reuse; beneficiary reuse; missing provenance; canonical hash mismatch; deterministic replay; quarantine record; review-required finding; all nine live-authority fields denied; effectful input denied; and input-order independence.

## Recovery and no-go conditions

A malformed or mismatched aggregate fails closed. Findings are append-only, idempotently replayable, and scoped to their source records. Stop for external calls, authority widening, cross-venture leakage not detected, nondeterministic findings, mutable source records, missing evidence hashes, or failed quarantine/review attribution.

## Human authorization

P6.3 planning and implementation authorization was provided on 2026-09-19. P6.3 acceptance remains separate. P6.4 remains blocked until P6.3 acceptance and separate authorization.
