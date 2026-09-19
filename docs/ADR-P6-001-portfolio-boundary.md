# ADR-P6-001 — Portfolio Boundary and Shared-Service Authority

**Status:** Proposed with Phase 6 planning
**Date:** 2026-09-19

## Decision

P6 will represent portfolio coordination and shared services as explicit,
typed, kernel-checked records. Portfolio aggregation is a reporting and
governance boundary, not a new source of authority. Shared services are
stateless synthetic runners with explicit venture scope, quotas, expiry, and
provenance.

## Consequences

- Portfolio views may aggregate only allowlisted metadata.
- Venture-private state and grants remain isolated.
- Shared-service outputs cannot grant capabilities or mutate another venture.
- P5 balances remain non-spendable and cannot be harvested into real capital.
- Quarantine and wind-down are selective and auditable.
- Configuration fingerprints and taint remain mandatory across all derived
  records.

## Rejected alternatives

- Ambient shared-service authority.
- Portfolio-wide credentials or mutable cross-venture state.
- Treating an aggregate report as authorization.
- Introducing provider integration during P6.
