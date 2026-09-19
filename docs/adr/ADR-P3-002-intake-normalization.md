# ADR-P3-002 — Voyage Scout Intake and Normalization

**Status:** Proposed for P3.1 review
**Date:** 2026-09-19

## Decision

P3.1 consumes P2 Opportunity and Thesis records through a separate, read-only
source boundary. It validates the P2 JSON Schema contracts, portfolio scope,
configuration fingerprint, freshness, source hashes, and opportunity-to-thesis
cross-references before normalizing records for later Scout reasoning.

The P3.1 store is separate from P2 state. It is append-only for retained raw
records and transformation lineage; no P2 record is updated, deleted, or
reclassified.

## Idempotency

The intake identity is the SHA-256 digest of the opportunity-set ID, thesis-set
ID, and Scout portfolio. A repeat delivery with the same canonical payload
returns the existing normalized record. Reusing that identity with different
content raises an idempotency conflict. Raw record IDs are immutable and a
changed raw envelope raises a mutation error.

## Normalization

Normalization trims repeated whitespace in opportunity statements and copies
the six P2 thesis dimensions into a bounded normalized structure. It preserves
the original opportunity, thesis, and evidence envelopes, source hashes,
taint status, and a transformation row for every source record. Tainted input
remains tainted. No normalized field is an authorization field.

## Rejection behavior

The intake rejects duplicate IDs, stale records, future timestamps,
cross-portfolio records, configuration mismatches, invalid P2 contracts,
missing evidence references, and thesis references to absent opportunities.

## Non-goals

P3.1 does not score, accept, reject, launch, spawn, allocate capital, execute
payments, call brokers, request credentials, contact customers, or perform any
external action. It does not modify P2 state.
