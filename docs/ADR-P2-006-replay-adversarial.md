# ADR-P2-006: Durable Replay and Adversarial Verification

**Status:** Accepted for P2.5 implementation
**Date:** 2026-09-18
**Scope:** Shadow reasoning, synthetic integration, and evidence production only

## Context

P2.5 must reproduce decisions from durable state and demonstrate expected
rejection of tampered, stale, contradictory, duplicate, cross-portfolio, and
authority-widening inputs. Replay must not become an execution path.

## Decision

Use a versioned ReplayCoordinator with:

- schema-validated replay requests;
- policy and configuration fingerprint matching;
- portfolio-scope checks on requests and source records;
- deterministic canonical result hashing;
- duplicate request convergence;
- an append-only, hash-chained replay result ledger;
- recursive rejection of truthy authority fields;
- no external side effects or authority output.

The synthetic SQLite implementation is mirrored by
migrations/p2/005_replay_adversarial.sql.

## Consequences

Replay results are reproducible and tamper-evident. Rejected inputs remain
available for audit as failure evidence without being transformed into
authorization. Stale and contradictory evidence is rejected by the existing
P2.1/P2.2 boundaries before it can become replay input.

## Rollback and quarantine

A replay failure quarantines the request/result record for operator review. It
does not delete source evidence, rewrite historical transitions, or retry an
unauthorized operation. Corrections require a new idempotency key and preserve
the original failure record.
