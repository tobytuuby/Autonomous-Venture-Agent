# P2.1 Opportunity Intake Review Record

**Status:** Implementation evidence produced; operator review pending  
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

This record is not a P2.1 completion decision. A delegated analyst/auditor or
project operator must review the implementation, migration, fixtures, and test
evidence before P2.1 is marked complete and P2.2 begins.
