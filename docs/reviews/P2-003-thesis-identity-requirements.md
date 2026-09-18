# P2.3 Thesis Identity Requirements Review

**Status:** Requirements reviewed; implementation authorized
**Date:** 2026-09-18
**Increment:** P2.3 — Thesis identity
**Predecessor:** P2.2 accepted under delegated analyst/auditor authority

## Requirements recorded

- Deterministic SHA-256 fingerprint over six canonical dimensions.
- Immutable identity with idempotent repeated derivation.
- Complete normalized-evidence to dimension-assignment to thesis lineage.
- Portfolio isolation and append-only assignment/lineage records.
- Contradiction surfacing before unified thesis creation.
- Taint and evidence-type preservation.
- No authorization, venture, capital, payment, worker, broker, credential, or
  external-action fields or paths.

## Implementation decision

The requirements are sufficient to implement P2.3 as a SQLite synthetic
integration shape mirrored by a versioned PostgreSQL migration. The classifier
uses built-in claim-key rules and preserves unclassified claims as assumptions.
P2.3 remains shadow-only.
