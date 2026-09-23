# P7.5 Worker Authority Boundary — Implementation Plan

## Plan status

Planning artifact only. No implementation authorization is recorded. The plan must be reviewed and accepted before source changes begin.

## Increment 1 — Contract and identity model

Define a secret-free worker descriptor, admission envelope, task envelope, capability envelope, provenance record, revocation record, quarantine record, and recovery record. Reconcile them with the existing P3 worker-archetype, manager-envelope, sandbox-descriptor, P6 coordination, and P7 evidence conventions without weakening any existing invariant.

No runnable worker is created in this increment.

## Increment 2 — Synthetic admission boundary

Implement a standard-library-only fixture that records, validates, denies, and quarantines synthetic worker admission. Admission must bind worker, manager, venture, portfolio, archetype, policy, configuration, provenance, correlation, and idempotency identities. It must reject missing, stale, mismatched, cross-venture, live, or authority-bearing inputs.

## Increment 3 — Capability and task boundary

Implement non-widening capability-envelope validation and effect-free task recording. The fixture must reject self-escalation, delegated grant minting, model-output approval, authority-bearing task fields, expired or replayed packets, and all nine live authorities. It must never dispatch work.

## Increment 4 — Revocation, replay, and isolation

Implement synthetic revocation and quarantine records, idempotent replay handling, collision detection, parent-scope revocation propagation, and cross-venture isolation checks. Revocation and quarantine must survive simulated retry and restart from the authoritative synthetic record.

## Increment 5 — Failure and recovery

Exercise admission failure, capability failure, provenance failure, revocation failure, duplicate/replay collision, partial-write, crash/restart, stale-state, and cross-venture failure. Every failure must leave the fixture denied or quarantined, preserve evidence, and prevent authority restoration.

## Increment 6 — Evidence and review packet

Generate the focused log, full-regression log, 93 case envelopes, source and test inventories, authority/recovery matrices, execution manifest, technical report, governance assessment, independent-review template, and final acceptance decision only after independent review. Planning and implementation commits must remain separately identifiable.

## Forbidden shortcuts

Do not attach a real CEO, spawn a real or runnable worker, enable worker authority, call an external system, begin P7.6, or treat a passing unit test or model response as authorization.
