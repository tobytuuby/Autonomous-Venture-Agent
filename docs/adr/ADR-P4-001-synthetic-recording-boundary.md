# ADR-P4-001 — Synthetic Recording Boundary

**Status:** Proposed for P4.0 review
**Date:** 2026-09-19

## Decision

The first P4 increment is a synthetic, recording-only boundary. It accepts
structured rehearsal records, preserves provenance, enforces configuration
fingerprints, converges duplicate delivery by idempotency key, and produces
no external effect.

## Authority constraints

P4.0 explicitly denies capital allocation, venture creation, worker spawning,
broker execution, payment, credential access, deployment, customer contact,
and all other external actions. The adapter contains no network or provider
client. A human-review flag is required in the record, but recording a
rehearsal is not an approval and does not create live authority.

## Evidence and recovery

Each record retains the request payload, provenance source IDs and hashes,
taint status, configuration fingerprint, canonical record hash, and recorded
timestamp. Duplicate delivery returns the existing record. Reuse of an
idempotency key with different content fails closed.

## Exit conditions

P4.0 is not complete until its tests, negative tests, evidence manifest,
regression run, and independent human review are recorded. P4.0 acceptance
does not authorize live external actions.
