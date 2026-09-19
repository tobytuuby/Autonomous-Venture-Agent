# ADR-P5-001: Synthetic Financial Boundary

## Status

Accepted for P5.0 implementation only.

## Decision

P5.0 records synthetic revenue events in a durable SQLite ledger. It never
moves funds, calls a provider, uses credentials, contacts customers, or grants
financial authority. The ledger is an evidence boundary, not authoritative
production money state.

## Controls

- typed event and ledger schemas;
- immutable event identity and idempotency key;
- canonical event hash and collision denial;
- required provenance and configuration fingerprint;
- append-only SQLite record storage;
- explicit denial of all nine live-authority fields;
- no network or provider client.

## Consequences

P5.0 can prove synthetic event durability and replay behavior. It cannot prove
revenue collection, payment settlement, treasury operations, customer behavior,
or production financial readiness.
