# P2.1 Opportunity Intake Review Record

**Status:** ACCEPTED — delegated analyst/auditor review
**Increment:** P2.1 — Opportunity intake  
**Date:** 2026-09-18

## Scope

- Typed opportunity and evidence-envelope validation
- Idempotency and exact duplicate convergence
- Source hash verification
- Freshness enforcement
- Portfolio-scope enforcement
- Synthetic durable intake store and PostgreSQL migration shape
- Negative tests for tampered, stale, conflicting, duplicate, and cross-scope inputs

## Evidence

- P2.1 tests: 7 passed.
- Full repository suite including P2.0/P2.1 tests: 91 passed.
- All four source types are accepted as typed evidence.
- Exact duplicate delivery produces one durable opportunity record and a
  second hash-chained duplicate event.
- Idempotency-key conflicts and changed duplicate identities are rejected.
- Tampered source payloads, stale evidence, and cross-scope evidence are rejected
  before opportunity persistence.
- Intake results explicitly report `external_action_authorized: false`.
- No external service, broker, payment, credential, venture, worker, or live
  network path is used.

## Decision

P2.1 is **ACCEPTED** on 2026-09-18 under explicit operator delegation to the
analyst/auditor role. The implementation satisfies typed intake, idempotency,
provenance preservation, freshness, source-integrity, and scope-isolation
requirements.

Repository corrections to the supplied review: the authoritative migration
shape is `migrations/p2/001_opportunity_intake.sql`, not `008_p2_intake.sql`;
the store default freshness window is 30 days, while the one-hour value is
used only by the stale-evidence test. The review record itself is the delegated
acceptance record; it does not claim an independent human identity beyond the
operator's delegation.

P2.1 exit is recorded. P2.2 — Evidence normalization is authorized to begin
under the existing shadow-only, synthetic-only, provenance-preserving, and
zero-external-action restrictions.
