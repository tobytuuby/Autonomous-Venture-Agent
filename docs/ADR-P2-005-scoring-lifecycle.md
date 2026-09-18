# ADR-P2-005: Deterministic Scoring and Lifecycle

**Status:** Accepted for P2.4 implementation
**Date:** 2026-09-18

## Decision

P2.4 uses versioned weighted coverage scoring over the six P2.3 thesis
dimensions. Scores include a content-addressed input fingerprint, weights,
dimension contributions, reasons, uncertainty, taint summary, and contradiction
count. Confidence intervals widen for tainted or contradictory evidence.

Lifecycle transitions use a fixed legal transition matrix and durable state.
Transitions, human review decisions, and replay events are append-only. Terminal
states cannot be mutated. Accepted means that the thesis passed a portfolio
analysis threshold; it is never venture, capital, payment, worker, broker,
credential, CEO, or external-action authorization.

The implementation is a SQLite synthetic integration shape mirrored by
migrations/p2/004_thesis_scoring.sql for durable deployment planning.
