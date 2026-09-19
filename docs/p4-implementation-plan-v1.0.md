# Phase 4 Implementation Plan v1.0

**Increment:** P4.0 — Synthetic recording boundary
**Status:** Implementation in progress
**Scope:** Synthetic, sandbox-only, recording-only

## Deliverables

- P4 synthetic-action-record schema.
- Durable recording store with idempotency and provenance preservation.
- Fail-closed denial of all external-action fields.
- ADR-P4-001.
- Positive and negative tests.
- P4.0 evidence manifest and certification review.

## Explicit non-goals

This increment does not enable capital allocation, venture creation, worker
spawning, broker execution, payment, credential access, deployment, customer
contact, customer data access, or any external action. It does not modify P2
state or change P3 scoring authority.

## Exit gates

- All P4.0 tests pass.
- Full P0–P3 regression passes.
- Duplicate and collision behavior is proven.
- Provenance and configuration fingerprint are reconstructible.
- Every prohibited authority field is denied.
- Human review remains required for any future approval workflow.
