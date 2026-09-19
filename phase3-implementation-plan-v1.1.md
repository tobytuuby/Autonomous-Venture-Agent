# Autonomous Venture Agent — Phase 3 Implementation Plan

## v1.1 — P3.1

**Status:** P3.1 active; acceptance review pending
**Predecessor:** phase3-implementation-plan-v1.0.md
**Execution class:** Synthetic integration and shadow reasoning only

## Scope

P3.1 implements the Voyage Scout intake boundary. It consumes P2 opportunity,
thesis, and evidence records read-only; validates their contracts, scope,
freshness, hashes, and cross-references; and emits a bounded normalized record
for later P3.2 scoring work.

## Deliverables

- kernel/scout/intake.py and kernel/scout/__init__.py
- schemas/p3/scout-opportunity-set.schema.json
- schemas/p3/scout-thesis-set.schema.json
- schemas/p3/scout-normalized-intake.schema.json
- tests/p3/test_p3_1_intake.py and P3.1 fixtures
- docs/adr/ADR-P3-002-intake-normalization.md
- tests/certification/p3-raw/P3-1.json and P3.1 evidence manifest

No migration is introduced. The store is a separate synthetic SQLite boundary
used for P3.1 evidence and does not mutate P2 state.

## P3.1 denominator

P3.1 has its own denominator. It is not added to P2's 41 tests, P0/P1 ADV
denominators, or P3.0's 6-test denominator.

## Exit conditions

- normal intake validates and normalizes opportunity/thesis/evidence records;
- duplicate delivery converges and collision is rejected;
- stale, invalid, cross-scope, and cross-reference inputs are denied;
- raw records and transformation lineage are retained;
- taint remains preserved and event-chain replay verifies;
- all P3.1 tests and full regression pass;
- analyst/auditor review records the decision and limitations.
