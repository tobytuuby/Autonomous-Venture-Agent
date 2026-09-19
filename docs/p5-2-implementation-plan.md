# P5.2 Implementation Plan — Synthetic Treasury Simulation

**Status:** Planning authorized; implementation not authorized
**Prerequisite:** Accepted P5.1 at 4a34663a0929eb87834b04908c945abb67c5d45a
**Execution class:** Synthetic only
**Policy scope:** FIN-505 and FIN-509

## Objective

Define a deterministic, durable, non-spendable treasury simulation derived from
accepted P5.1 reconciliation receipts. The simulation may calculate reserves,
deployable balances, ceilings, and proposed allocations, but it must never
move funds, authorize a payment, contact a broker, access credentials, or
create a live venture or worker.

## Planned artifacts

- `kernel/p5/treasury.py`: synthetic treasury state machine and invariant checks.
- `schemas/p5/synthetic-treasury-state.schema.json`: receipt/state schema.
- `tests/p5/test_p5_2_treasury.py`: focused boundary and recovery tests.
- `tests/certification/p5-2-manifest.json`: test and evidence manifest.
- `tests/certification/p5-raw/P5-2.json`: raw synthetic evidence.
- `docs/p5-2-certification-report.md`: implementation evidence, not acceptance.
- A separately signed P5.2 entry decision before implementation begins.

## Required invariants

1. Inputs must be accepted synthetic reconciliation receipts with matching
   configuration fingerprints.
2. Balances are informational, non-spendable, and carry `effect: "none"`.
3. Reserve floors and deployable ceilings are deterministic and cannot be
   bypassed by replay, ordering, or duplicate delivery.
4. Allocations are bounded by the configured ceiling and are never increased by
   recovery or replay.
5. Ratchet behavior is monotonic: committed constraints cannot be loosened by
   later inputs.
6. Invalid, stale, cross-venture, cross-configuration, or authority-bearing
   inputs fail closed before state mutation.
7. Every state transition preserves source hashes, provenance, taint, and the
   configuration fingerprint.
8. SQLite persistence must support crash recovery and idempotent replay without
   producing a second state transition.

## Planned focused tests

- valid synthetic treasury calculation;
- deterministic result under reordered receipts;
- duplicate replay convergence;
- stale or changed receipt collision denial;
- reserve-floor enforcement;
- deployable-ceiling enforcement;
- monotonic ratchet enforcement;
- cross-venture and cross-configuration denial;
- provenance and taint preservation;
- crash recovery after durable state write;
- denial of all live-authority fields;
- denial of any spendable or effectful result.

## Explicit non-goals

P5.2 will not integrate a payment provider, broker, bank, wallet, credential
store, deployment service, customer channel, capital transfer, venture
executor, worker launcher, or external network. It will not unlock P5.3 or P5.4.

## Acceptance gate

P5.2 implementation may begin only after a signed human authorization is
committed. Completion will require focused tests, full regression, schema and
manifest validation, raw evidence, clean diff checks, and a separate formal
human acceptance decision.
