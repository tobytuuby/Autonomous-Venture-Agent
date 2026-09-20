# Phase 6 Policy Specification v1.4 — P6.4

P6.4 policy codes: OPS-601 selective scope isolation, OPS-602 quarantine and grant revocation, OPS-603 deterministic recovery, OPS-604 synthetic harvest and reinvestment proposals, OPS-605 wind-down evidence, OPS-610 provenance continuity, OPS-612 fail-closed authority, OPS-613 evidence separation.

All operations must be synthetic-only, effect-free, capability-denied, provenance-complete, fingerprint-matched, and scoped to one portfolio and venture. Service freezes may target one service class. A venture freeze must not alter unrelated ventures. Quarantine findings require preserved reason and evidence hash. Recovery may record state only after quarantine and must not restore authority. Harvest and reinvestment are proposals/records, never execution. Wind-down is a record, never an external action.

Any truthy live-authority field, effect other than none, missing provenance, fingerprint mismatch, cross-scope target, changed idempotency content, or non-deterministic replay is a denial. No provider or test-provider integration is permitted.
