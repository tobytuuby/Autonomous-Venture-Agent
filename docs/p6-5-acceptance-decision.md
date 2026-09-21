# P6.5 Acceptance Decision

**Date:** 2026-09-21  
**Reviewer:** Kalaap Das  
**Status:** ACCEPTED — synthetic-only scope  
**Evidence-complete commit:** `89b2399291a48393c6ec3b1092b3b202e3fbfe68`

## Decision

P6.5 is accepted for its defined synthetic end-to-end certification scope.

## Basis

- Focused P6.5 tests: 12/12 passed.
- Combined P6.0–P6.5 regression: 116/116 passed.
- Full repository regression: 337/337 passed.
- Two synthetic ventures and one stateless shared service were composed.
- Cross-venture leakage was detected and quarantined.
- Selective recovery, synthetic harvest, and reinvestment proposal behavior were verified.
- All nine live-authority fields remained denied.
- The implementation and evidence package were independently reviewed.
- Six pre-existing SQLite ResourceWarning messages were documented; no test failures occurred.

The acceptance is limited to the synthetic, effect-free, fail-closed P6.5 scope. It does not authorize providers, credentials, network, payments, brokers, customers, deployment, capital movement, real ventures, workers, or production operation.

Tag `P6.5-ACCEPTED` records this decision. P7 has not started and remains separately gated.
