# ADR-P2-003: Derived Evidence Normalization

**Status:** Accepted for P2.2 implementation  
**Date:** 2026-09-18

## Decision

P2.2 stores immutable raw envelopes separately from normalized derived records.
A normalized record contains raw evidence IDs, source hashes, a deterministic
normalized hash, and an append-only transformation lineage. Duplicate
normalization converges by normalized hash.

Taint is monotonic: the strongest taint among inputs is retained. Source type is
copied from the evidence contract and cannot be changed by a payload or model
instruction. Contradictions are recorded and surfaced as references; neither
source is overwritten or silently preferred.

The implementation is a SQLite synthetic integration shape mirrored by
migrations/p2/002_evidence_normalization.sql for durable deployment planning.
No external action, venture, worker, capital, payment, broker, credential, or CEO
authority is represented or created.
