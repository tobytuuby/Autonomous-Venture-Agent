# Phase 3 Evidence Manifest

**Status:** READY FOR HUMAN CERTIFICATION REVIEW
**Manifest scope:** P3.0–P3.2
**Baseline:** c6d1eb3d2b18d47e54d1ece50452ea093c949eae
**Execution class:** Synthetic integration and shadow reasoning only

## Denominator

| Increment | Result |
|---|---:|
| P3.0 contracts | 6/6 |
| P3.1 intake and normalization | 13/13 |
| P3.2 scoring and lifecycle | 23/23 |
| Full discovered regression | 161/161 |

The P3 denominator is separate from P0/P1 ADV evidence and the P2 41-test
denominator.

## Artifact inventory

The repository contains 13 P3 schemas in the implemented baseline. The
inventory is six P3.0 schemas, three P3.1 schemas, and four P3.2 schemas.

### Governing and status documents

- phase3-policy-spec-v1.0.md
- phase3-implementation-plan-v1.0.md
- phase3-implementation-plan-v1.1.md
- phase3-implementation-plan-v1.2.md
- docs/PHASE3_STATUS.md
- docs/adr/ADR-P3-001-contract-boundary.md
- docs/adr/ADR-P3-002-intake-normalization.md
- docs/adr/ADR-P3-003-scoring-lifecycle.md

### P3.0 schemas and fixtures

- schemas/p3/common.schema.json
- schemas/p3/venture-identity.schema.json
- schemas/p3/sandbox-descriptor.schema.json
- schemas/p3/manager-envelope.schema.json
- schemas/p3/worker-archetype.schema.json
- schemas/p3/provisioning-request.schema.json
- tests/p3/fixtures/p3-0-contract-fixtures.json
- tests/p3/test_p3_contracts.py

### P3.1 schemas, fixtures, code, and evidence

- kernel/scout/__init__.py
- kernel/scout/intake.py
- schemas/p3/scout-opportunity-set.schema.json
- schemas/p3/scout-thesis-set.schema.json
- schemas/p3/scout-normalized-intake.schema.json
- tests/p3/fixtures/p3-1-intake-fixtures.json
- tests/p3/test_p3_1_intake.py
- tests/certification/p3-1-manifest.json
- tests/certification/p3-raw/P3-1.json

The P3.1 scenario fixture contains 12 scenarios. Its raw archive is 2,195
bytes and its manifest is 2,056 bytes, 4,251 bytes combined.

### P3.2 schemas, fixtures, code, and evidence

- kernel/scout/scoring.py
- schemas/p3/scoring-weight-set.schema.json
- schemas/p3/voyage-candidate.schema.json
- schemas/p3/lifecycle-transition.schema.json
- schemas/p3/review-decision.schema.json
- tests/p3/fixtures/p3-2-scoring-fixtures.json
- tests/p3/test_p3_2_scoring.py
- tests/certification/p3-2-manifest.json
- tests/certification/p3-raw/P3-2.json

The P3.2 scenario fixture contains 24 scenarios. Its raw archive is 2,118
bytes and its manifest is 1,210 bytes, 3,328 bytes combined.

## Evidence structure

1. P2 raw opportunity, thesis, and evidence envelopes are retained by the
   separate P3.1 intake boundary.
2. P3.1 records source hashes, taint status, normalized output, and
   transformation rows.
3. P3.2 consumes the normalized record and retains score inputs, frozen
   weights, factor contributions, uncertainty interval, and candidate state.
4. Lifecycle transitions retain from-state, to-state, actor, role, timestamp,
   reason, and human-review flag.
5. Quarantine records contradiction identifiers and the second occurrence adds
   an escalation marker.
6. P3.3 reports and manifests preserve the source commit and artifact hashes.

## Key source hashes

| Artifact | SHA-256 |
|---|---|
| phase3-policy-spec-v1.0.md | 1bab7c6d1da52871285c9f7e5279eccf1607d9dc9995ac116eb15b31e38a46a1 |
| phase3-implementation-plan-v1.2.md | 10ebd9b121a3b39269b9a02232500e7a5638c0cb84f269d4513b5d1ae6f22517 |
| kernel/scout/intake.py | f4fb81717f4832b8c5aac318b733bb5612a5b9995bfc9466ae6dce2b03842a55 |
| kernel/scout/scoring.py | 153c793e0dcf7260a2c6e136af658a6719fc4995715d8b88a47df6d214fcac05 |
| P3.0 contract test | f1d48b5561459d5ff04b5fed5dfea669c93eb087fa2ccf7a9680e1ffa04a6bd8 |
| P3.1 test | 090d16cd892842214f8d56a8208b583db4f869cb8814314d1610bb3feabab818 |
| P3.2 test | 7f30f0e10532ddd4dcde9d4104feeffcffe208e49d76c1587a3ae10287d5f84e |
| P3.1 raw evidence | 21fbfd6c5e619df0861d5a7495c15e4337e5531b7386f350769ed2f81b46e5c9 |
| P3.2 raw evidence | 3da3f64e19d8a81436814adedbb23714c08c93970e96d2b3fb5a81b99a8b7dc9 |

## Limitations

This manifest proves the committed synthetic evidence inventory and test
results. It does not prove live venture operation, production sandbox
isolation, real-provider reachability, capital readiness, broker readiness,
payment readiness, or P4 authority.
