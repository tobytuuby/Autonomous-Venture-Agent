# ADR-P2-004: Deterministic Thesis Identity

**Status:** Accepted for P2.3 implementation
**Date:** 2026-09-18

## Decision

Derive thesis identity from exactly six canonical dimensions: category,
customer segment, core offer, monetization model, acquisition channel, and
assumptions. The fingerprint is SHA-256 over sorted, compact canonical JSON of
those dimensions only. The thesis ID is content-addressed from that fingerprint.

Dimension assignments retain normalized and raw evidence IDs, evidence type,
taint, scope, and reasoning. Thesis identity and lineage are immutable and
append-only. Repeated derivation converges by fingerprint and returns the
existing thesis identity.

Contradictory normalized evidence is surfaced before thesis creation and cannot
be silently merged. All records remain portfolio-scoped. This is an analysis
artifact only; no venture, launch, capital, payment, worker, broker,
credential, or external-action authority is represented.
