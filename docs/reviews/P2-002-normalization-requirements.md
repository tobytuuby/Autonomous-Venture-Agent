# P2.2 Evidence Normalization Requirements Review

**Status:** Requirements reviewed; implementation contract conditions recorded  
**Increment:** P2.2 — Evidence normalization  
**Date:** 2026-09-18  
**Predecessor:** P2.1 accepted under delegated analyst/auditor authority

## Review basis

- `phase2-policy-spec-v1.0.md`, OPP-002, OPP-008, OPP-009, OPP-012
- `phase2-implementation-plan-v1.3.md`
- P2 evidence-envelope contract under `schemas/p2/`
- P2.1 intake implementation, migration, ADR, and test evidence

## Requirements confirmed

1. **Raw-envelope preservation:** The original EvidenceEnvelope and its source
   hash remain immutable and addressable after normalization. Normalization may
   add a derived record but may not overwrite, delete, or silently rewrite the
   raw payload.
2. **Explicit normalized lineage:** Every normalized record references the raw
   evidence ID and source hash, records the normalization operation and actor,
   and carries a deterministic transformation-chain extension.
3. **Typed evidence preservation:** Evidence type remains one of external,
   synthetic, inferred, or operator. A model summary cannot change the type.
4. **Monotonic taint:** Taint cannot be reduced by normalization or
   summarization. A derived record is tainted if any input is tainted. Any
   declassification remains an explicit authenticated human-operator action
   with an auditable decision identifier.
5. **Freshness and contradiction handling:** Freshness metadata is retained.
   Contradictory sources are represented as evidence with contradiction
   references/status; they are not deleted or resolved by silently choosing a
   preferred source.
6. **Instruction-smuggling containment:** Instructions found inside external or
   untrusted evidence remain content/evidence. They cannot alter policy,
   capabilities, actor role, portfolio scope, or execution authority.
7. **Scope and authority:** Normalization is portfolio-scoped and cannot create
   ventures, workers, capital requests, payments, broker calls, credentials, or
   external actions.
8. **Replayability:** The normalized result is deterministic for fixed raw
   evidence, normalization policy, and configuration fingerprint.

## Required implementation artifacts

P2.2 implementation must add:

- A versioned normalized-evidence contract under `schemas/p2/`.
- A normalization service with append-only raw-to-derived lineage.
- Contradiction and instruction-smuggling fixtures.
- Negative tests for taint reduction, raw-envelope mutation, cross-scope
  normalization, and authority widening.
- A migration only if durable normalized records require new state; otherwise a
  versioned migration determination.
- ADR-P2-003 and a P2.2 review record.
- Updated P2 status evidence and exact test results.

## Review decision

The P2.2 requirements are sufficiently defined to begin implementation under
these conditions. P2.2 remains shadow/synthetic only. No lifecycle acceptance,
thesis scoring, venture formation, capital, payment, broker, credential, or
external-action behavior is authorized by this requirements review.
