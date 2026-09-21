# Phase 6 Implementation Plan v1.6 — P6.5 End-to-End Certification

**Status:** P6.5 implementation accepted for synthetic-only scope.
**Execution class:** Synthetic-only.
**Baseline:** `b77d7e17260d6b4519d1b574f68d130815300c48`.
**Locked configuration fingerprint:** `8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11`.

## Scope

P6.5 composes the accepted P6.0–P6.4 components across two synthetic ventures and one stateless `metadata-read` service. The composition creates typed coordination packets, service demands and outputs, a cross-venture anomaly finding, selective quarantine/recovery for one venture, and synthetic harvest/reinvestment records for the other.

## Implementation increments

1. Add `SyntheticPortfolioCertification` as a kernel-owned composition harness.
2. Add focused tests for composition, attribution, isolation, anomaly/quarantine, recovery, harvest/reinvestment, determinism, provenance, schema-compatible flags, and authority denial.
3. Preserve raw execution evidence and separate technical/non-technical assessments.
4. Run focused P6.5, combined P6.0–P6.5, and full repository regressions.
5. Leave P6.5 unaccepted pending explicit human review; do not create `P6.5-ACCEPTED`.

## Stop conditions

Stop on any external call, live-authority field, effectful output, cross-venture leakage not detected, nondeterminism, missing provenance/fingerprint continuity, private metadata exposure, or failed recovery/isolation.
