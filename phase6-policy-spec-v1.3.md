# Phase 6 Policy Specification v1.3 — P6.3 Addendum

Status: adopted for P6.3 implementation. No live-authority change.

P6.3 operationalizes aggregate anomaly controls under PORT-602 isolation, PORT-604 bounded coordination, PORT-610 provenance, PORT-612 fail-closed authority, and PORT-613 evidence separation.

## Rules

- Analysis inputs must share one portfolio scope and one configuration fingerprint.
- Venture identifiers must remain attached to every source record.
- Cross-venture leakage, drift, duplicate/structuring-like patterns, stale evidence, quota exhaustion, configuration mismatch, counterparty reuse, and beneficiary reuse produce deterministic findings.
- Findings are either NO_ANOMALY, REVIEW_REQUIRED, or QUARANTINED.
- Quarantine is a finding record, not execution and not an authority grant.
- Exact replay converges to identical finding hashes.
- Missing provenance, changed input hashes, mixed fingerprints, effectful input, and live-authority fields fail closed.
- All nine live-authority fields remain denied.

## Recovery

No source record is altered. A finding can be replayed from canonical inputs, and a quarantine/review record preserves reason, source hashes, scope, taint, lineage, and evidence hash.
