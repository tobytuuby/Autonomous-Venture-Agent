# P2.4 Scoring and Lifecycle Requirements Review

**Status:** Requirements reviewed; implementation authorized
**Date:** 2026-09-18
**Increment:** P2.4 — Scoring and lifecycle
**Predecessor:** P2.3 accepted under delegated analyst/auditor authority

## Review basis

- phase2-policy-spec-v1.0.md, OPP-004 through OPP-012
- phase2-implementation-plan-v1.7.md
- P2.0 ThesisScore, ReviewDecision, and LifecycleTransition contracts
- P2.1 intake, P2.2 normalization, and P2.3 thesis identity artifacts

## Requirements confirmed

1. **Deterministic scoring:** For fixed thesis identity, evidence IDs, policy
   version, configuration fingerprint, algorithm version, weights, and input
   values, the score and all dimension scores are reproducible. The score must
   include a deterministic input/configuration fingerprint.
2. **Explainability:** Every score records dimension scores, normalized weights,
   uncertainty label and basis, evidence IDs, taint summary, and reviewer-visible
   reasons. Weight totals and score bounds are validated.
3. **Evidence preservation:** Scoring reads P2.3 thesis and lineage records. It
   does not mutate thesis identity, normalized evidence, or raw evidence.
   Tainted or contradictory evidence cannot become trusted because it was scored.
4. **Human review boundary:** A ReviewDecision requires an explicit
   human-operator reviewer, rationale, evidence references, and one of
   accepted/rejected/needs_review. The existing authorization fields remain
   present only as explicit false constants; acceptance is portfolio analysis,
   not venture approval.
5. **Deterministic lifecycle:** Lifecycle transitions are validated against a
   versioned legal transition matrix. Invalid transitions, self-transitions,
   cross-portfolio transitions, and transitions without evidence/reason are
   rejected.
6. **Quarantine and expiration:** Stale, contradictory, unsafe, or
   policy-invalid evidence can move a thesis to quarantined or expired without
   deleting score, thesis, evidence, or prior transition history.
7. **Supersession:** A replacement identity or materially changed thesis is
   represented by a new record and a superseded transition; the prior thesis is
   never mutated.
8. **Authority isolation:** No score, review, or lifecycle state can authorize
   venture creation, launch, capital, payment, worker spawning, broker calls,
   credentials, or external actions. Accepted means accepted for portfolio
   analysis only.
9. **Portfolio isolation:** Thesis, score, review, evidence, and transition
   portfolio IDs must match before any state is persisted.
10. **Human auditability:** Material review and lifecycle decisions persist actor,
    timestamp, rationale/reason, policy/configuration versions, evidence IDs, and
    correlation/idempotency identifiers.

## Required implementation artifacts

- Versioned ThesisScore, ReviewDecision, and LifecycleTransition validation
  contracts or compatible extensions.
- A versioned scoring configuration containing weights, score algorithm version,
  uncertainty rules, and authority effect none.
- Scoring and lifecycle services under kernel/opportunity/.
- Migration migrations/p2/004_scoring_lifecycle.sql if durable score/review/
  transition records require new state.
- ADR-P2-005 and implementation/acceptance review records.
- Synthetic fixtures for deterministic scores, tainted/contradictory evidence,
  valid and invalid transitions, quarantine, expiration, supersession, and
  cross-scope attempts.

## Required exit tests

1. Same thesis/evidence/configuration produces identical score and input hash.
2. Score weights, bounds, uncertainty, reasons, taint, and evidence references
   are explainable and schema-valid.
3. Scoring cannot mutate thesis or evidence records.
4. Review decisions require human rationale and retain all authority denials.
5. Legal lifecycle transitions succeed; illegal transitions are rejected.
6. Cross-portfolio scoring, review, and transitions are rejected before state
   changes.
7. Contradictory or stale evidence cannot produce an accepted thesis without
   explicit review handling and is quarantinable without deletion.
8. Supersession and expiration preserve prior records and append transitions;
   no external-action or venture-authority path exists.

## Decision

The P2.4 requirements are sufficiently defined to begin implementation. P2.4
remains shadow-only, synthetic-only, and evidence-production-only. No P3 work
or venture authority is authorized by this requirements review.
