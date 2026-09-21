# Autonomous Venture Agent — P7.1 Policy Specification

## v1.0

**Status:** Proposed for review; not implementation authorization.
**Phase:** P7.1 — Topology and deployment controls
**Predecessor:** Independently certified P7.0 at 47ad0ccb1ca33db3a54092c5c3faed1a2e037d86
**Execution class:** Synthetic, shadow, or isolated pre-production only
**Live authority:** All nine live-authority fields remain denied.

## 1. Purpose

P7.1 defines and verifies a production-shaped but isolated topology and the controls that admit, reject, roll back, and recover a release. It does not deploy the system to production and does not create or use live credentials.

P7.1 acceptance is deployment-control evidence only. It is not P8 authorization, production authorization, or authority-boundary expansion.

## 2. Scope

P7.1 covers:

- topology identity, component ownership, trust boundaries, and allowed paths;
- separation of source, policy, configuration, synthetic secrets, and runtime state;
- immutable release identity and configuration fingerprints;
- fail-closed deployment admission;
- synthetic release rehearsal and release evidence;
- rollback to a prior known-safe release;
- rollback after a partial deployment;
- denial of live, unauthorized, unreviewed, stale, or mismatched deployment requests;
- evidence preservation and independent review.

P7.1 does not cover backup/restore and disaster recovery as a phase objective; those belong to P7.2. It does not implement observability/incident response as a phase objective; those belong to P7.3. It does not create provider credentials or perform a live deployment.

## 3. Normative requirements

### P7.1-001 — Isolated topology

The topology MUST be represented by a versioned, secret-free manifest with component identities, ownership, trust boundaries, permitted communication edges, and execution class. Every fixture MUST be synthetic or isolated.

### P7.1-002 — Authority denial

The nine live authorities—network, broker, payment, credential, deployment, customer, capital, venture, and worker—MUST remain denied. A topology or deployment control MUST NOT provide an alternate path to any authority.

### P7.1-003 — Separation of concerns

Release source, policy, configuration, synthetic secret material, and authoritative runtime state MUST have distinct identities and hashes. A release MUST be rejected when any required identity is missing, stale, unexpectedly changed, or cross-environment.

### P7.1-004 — Release admission

Admission MUST be fail-closed unless the release is immutable, policy-compatible, configuration-compatible, synthetic-only, reviewer-approved, and bound to the declared topology. Model output MUST never satisfy approval.

### P7.1-005 — Deployment denial

Requests for live deployment, external side effects, missing approval, live credentials, unauthorized components, topology drift, or mismatched fingerprints MUST be denied before dispatch. Denial MUST produce an auditable, hash-linked result.

### P7.1-006 — Rollback

A failed or partially applied synthetic release MUST return to the prior known-safe release. Rollback MUST be idempotent, must not widen authority, and must preserve before/after release, topology, configuration, and authority fingerprints.

### P7.1-007 — Two-run gate

The exit gate requires two consecutive clean rehearsal runs from clean, independently identified starting states. Each run MUST include normal release admission, deployment-denial negatives, successful rollback, and evidence-hash verification.

### P7.1-008 — Evidence and review

Every case MUST record case ID, source/configuration/topology hashes, environment identity, command, timestamps, expected and observed disposition, authority result, raw output hash, and reviewer classification. The implementer MUST NOT be the sole reviewer.

## 4. Prohibitions

P7.1 MUST NOT:

- attach a real CEO;
- create or use live credentials;
- contact an external party;
- execute real deployment, network, broker, payment, customer, capital, venture, or worker actions;
- use a real provider or real customer;
- widen any authority boundary;
- use a model response as release approval;
- skip rollback or the two-consecutive-run gate;
- claim production readiness from a unit test alone.

## 5. Exit interpretation

A passing P7.1 result proves only that the specified topology and deployment controls behaved correctly in isolated rehearsal. It does not prove live deployment safety, provider availability, real-credential custody, financial safety, or P8 readiness.

## 6. Change control

Changes to execution class, topology trust boundaries, authority fields, release-admission conditions, rollback semantics, or the two-run gate require a new P7.1 policy revision and impact analysis.
