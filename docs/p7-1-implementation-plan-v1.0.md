# P7.1 Implementation Plan — Topology and Deployment Controls

## v1.0

**Status:** Proposed for review; planning artifact only.
**Implementation authorization:** Not recorded.
**Branch:** phase7/p7-0-blocking-drift until a separately authorized P7.1 implementation branch is created.
**Predecessor:** P7.0 independently certified, 337/337 full regression.

## 1. Required increments

### P7.1.0 — Topology and ownership contract

Create a versioned, secret-free topology manifest and schema. It must identify components, owners, execution class, trust boundaries, permitted edges, forbidden edges, and synthetic fixture identities.

Focused tests:
- manifest schema and required-field validation;
- component ownership and trust-boundary validation;
- forbidden-edge detection;
- topology fingerprint determinism.

### P7.1.1 — Configuration and release identity

Define release, policy, topology, configuration, synthetic-secret, and authoritative-state identities. Compute fingerprints without exposing secret values. Reject missing, stale, cross-environment, and mismatched fingerprints.

Focused tests:
- deterministic fingerprint generation;
- secret-free fingerprint output;
- stale and cross-environment rejection;
- source/policy/configuration/topology mismatch rejection;
- model-output-as-approval rejection.

### P7.1.2 — Deployment admission and denial boundary

Implement a synthetic deployment controller or adapter that accepts only a fully approved, immutable, synthetic release bound to the declared topology. It must deny live deployment, live credentials, external effects, missing approval, unauthorized components, and all nine live authorities before dispatch.

Focused tests:
- one approved synthetic release admission;
- nine direct authority-denial cases;
- nine attempted-use negative cases;
- live deployment and live-credential denial;
- external-side-effect sentinel remains untouched;
- denial evidence hash and audit record validation.

### P7.1.3 — Rollback and two-run rehearsal

Implement idempotent rollback to the prior known-safe synthetic release, including a partial-apply failure. Preserve before/after release and authority fingerprints and emit case-level evidence.

Focused tests:
- normal release then rollback;
- partial deployment then rollback;
- repeated rollback idempotency;
- rollback rejection for unknown or corrupted target;
- no authority widening during release or rollback;
- evidence preservation and hash verification.

## 2. Focused denominator

The focused suite MUST report at least these individually addressable cases:

| Case family | Minimum cases |
|---|---:|
| Topology/ownership contract | 8 |
| Identity/configuration separation | 10 |
| Admission and denial | 21 |
| Rollback and recovery | 10 |
| Two-run integration gate | 4 |
| **Minimum focused denominator** | **53** |

The 53 cases are a minimum evidence denominator, not a test-method count. Parameterized tests MUST emit one evidence envelope per case ID. The two-run integration gate MUST prove two consecutive clean runs; it must not collapse them into one assertion.

## 3. Required negative tests

At minimum, negative tests must cover:

- topology fingerprint mismatch;
- forbidden trust-boundary edge;
- source/policy/configuration mismatch;
- stale release;
- missing or invalid approval;
- approval supplied only by model output;
- live credential marker or non-synthetic credential;
- live deployment request;
- each of the nine live authorities;
- unauthorized component;
- external-side-effect sentinel activation;
- rollback target missing, corrupt, unknown, or already superseded;
- tampered evidence and duplicate case ID.

Any negative test that produces an external side effect fails the increment.

## 4. Recovery and rollback tests

The focused suite MUST include at least 10 recovery cases:

- normal rollback;
- rollback after partial apply;
- rollback after admission-time failure;
- rollback after post-apply verification failure;
- repeated rollback;
- rollback with an injected release-store failure;
- rollback with an injected evidence-write failure;
- rollback with an injected topology-read failure;
- rollback with an injected configuration-read failure;
- rollback with a stale rollback target.

Each case must record expected containment, observed state, before/after fingerprints, evidence hash, and whether the safe release was restored.

## 5. Evidence package

The implementation MUST add, without overwriting historical P7.0 evidence:

- a P7.1 topology manifest and schema;
- focused tests and synthetic fixtures;
- negative and recovery evidence;
- two-run rehearsal outputs;
- a P7.1 execution manifest and case-results JSONL;
- raw outputs with SHA-256 hashes;
- a technical certification report;
- a non-technical assessment;
- an independent review decision;
- a rollback/operator runbook;
- a status update and acceptance decision.

Every artifact must name the source commit, source-file hashes, configuration fingerprint, environment identity, command, timestamps, reviewer identity, and execution class.

## 6. Full-regression gate

Before P7.1 can be accepted:

1. run the focused suite and verify the declared case denominator;
2. run all required negative tests;
3. run all 10 recovery cases;
4. run two consecutive clean rehearsal runs;
5. independently verify evidence hashes and reviewer separation;
6. run the complete repository regression from the clean implementation commit;
7. record the exact full-regression denominator and zero failures/errors;
8. verify all nine live authorities remain denied and no external action occurred.

Any failure, unexplained warning, missing evidence field, authority widening, or external side effect blocks acceptance.

## 7. Forbidden shortcuts

No P7.2 work, P7.3 work, P7.4 work, P7.5 work, P7.6 certification, P8 entry, live credential, live deployment, or external action may begin under this plan.
