# Phase 6 Implementation Plan v1.4 — P6.4

## Scope

P6.4 implements synthetic, effect-free selective quarantine, harvest, reinvestment proposal, recovery, and wind-down records. It operates on explicit portfolio/venture/service scopes and preserves P6.0–P6.3 contracts as immutable inputs.

## Objectives and boundaries

- Freeze or quarantine one venture or one service class without affecting unrelated ventures or services.
- Record deterministic recovery attempts and explicit revocation of temporary grants.
- Produce synthetic harvest records and reinvestment proposals only; neither moves capital nor authorizes allocation.
- Record synthetic wind-down decisions and preserve evidence.
- Use append-only local journal state, deterministic hashes, idempotency, collision denial, provenance, taint, and the locked configuration fingerprint.
- Fail closed on scope, fingerprint, provenance, effect, schema, or authority violations.

No provider, credential, network, payment, broker, customer, deployment, capital, venture, worker, or live execution is permitted.

## Prerequisites

- P6.3 accepted at `3186f9650608ad98a1c573fe9fabaea2dc893573`.
- P6.0 registry, P6.1 coordination, P6.2 shared-service, and P6.3 anomaly contracts remain immutable.
- Locked fingerprint remains `8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11`.
- Explicit human authorization for P6.4 planning and implementation is recorded in `docs/p6-4-implementation-authorization.md`.

## Increments and sub-gates

- P6.4-A: operation envelope, canonical records, scope isolation, and authority-denial tests.
- P6.4-B: selective freeze/quarantine, idempotency, collision handling, and grant revocation.
- P6.4-C: deterministic recovery, synthetic harvest, reinvestment proposal, and wind-down records.
- P6.4-D: evidence manifest, raw outputs, technical certification, non-technical assessment, and full regression.
- Acceptance requires all sub-gates, separate evidence, clean bridge state, and explicit human acceptance. P6.5 remains blocked.

## Evidence and tests

The focused denominator is 18 tests. Evidence must include focused output, P6 regression output, full regression output, git state, configuration manifest, manifest hashes, and technical/non-technical reports. Raw outputs are immutable and separate from summaries.

## Recovery and rollback

Operations are append-only and replayable. On collision or invariant failure, no state is widened; the denial code, target scope, and evidence hash are preserved. Rollback means reverting the P6.4 commits or quarantining the affected synthetic scope; it never executes an external action. Recovery is idempotent and cannot restore live authority or spendability.

## Provenance continuity

Every record carries policy version, locked fingerprint, actor, portfolio/venture scope, correlation and idempotency keys, source IDs/hashes, lineage, taint, creation time, canonical hash, synthetic-only marker, effect none, and all live fields false.

## Explicit non-goals

No real quarantine, capital harvest, reinvestment, wind-down, service provider action, credential use, network access, customer contact, deployment, worker execution, or production readiness.

## Human authorization

P6.4 implementation authorization is required and recorded separately. P6.4 acceptance and any P6.5 authorization require new human decisions.
