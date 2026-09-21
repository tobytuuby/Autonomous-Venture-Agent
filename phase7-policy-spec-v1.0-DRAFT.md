# Autonomous Venture Agent — Phase 7 Policy Specification

## v1.0-DRAFT

**Status:** Draft for review; not canonical and not implementation authorization.  
**Phase:** P7 — Production readiness and controlled-integration preparation  
**Depends on:** accepted P6.5 boundary, `project-phase-plan-v2.1-DRAFT.md`, and `remaining-phases-implementation-plan-v1.1-DRAFT.md`  
**Execution class:** Pre-production rehearsal only  
**Live authority:** All nine live-authority fields remain denied.

## 1. Purpose

P7 determines whether the synthetic-only system is operationally ready for a separately approved P8 live pilot. P7 may use production-shaped topology and isolated fixtures, but it must not perform real external actions or create live credentials.

P7 acceptance is readiness evidence, not live authorization.

## 2. Normative requirements

### P7-001 — Synthetic-only execution

All P7 runs MUST use static, synthetic, shadow, or isolated/pre-production fixtures. Real customer, payment, capital, broker, deployment, credential, venture, worker, or network authority MUST remain unavailable.

### P7-002 — Nine-field authority denial

The following fields MUST remain denied and must be tested individually:

- network;
- broker;
- payment;
- credential;
- deployment;
- customer;
- capital;
- venture;
- worker.

A pass requires both a direct denial test and an attempted-use negative test for every field.

### P7-003 — Complete rehearsal matrix

P7.5 MUST test all nine fields across request, approval, dispatch, response, reconciliation, failure, freeze, revoke, quarantine, and wind-down states. The minimum matrix is 9 fields × 9 state families = 81 required cases; state-family fixtures may cover multiple fields only when each field has an independently asserted result.

### P7-004 — Test threshold

No required test may fail. Focused and full-regression denominators MUST be declared. Any failure, unauthorized action, unexplained authority widening, or unexplained ledger/provenance drift blocks P7 exit.

### P7-005 — Recovery

Freeze, revoke, quarantine, restore, rollback, and wind-down MUST each have one normal-path rehearsal and one injected-failure case. An unsafe live reversal may be simulated only with an approved limitation statement; simulation MUST NOT be reported as live proof.

### P7-006 — Evidence preservation

Each result MUST include source/configuration hashes, environment identity, command, timestamp, raw output location, and reviewer classification. Blocking drift evidence MUST be preserved within 15 minutes of detection and retained for the approved audit-retention period.

### P7-007 — Credential custody

P7 MUST prove kernel-owned custody, rotation, revocation, allowlisting, redaction, and fail-closed behavior using synthetic or isolated fixtures. No production credential may be created or stored.

### P7-008 — Independent review

The implementer MUST NOT be the sole reviewer for readiness, degraded-mode, or authority-boundary claims. The independent reviewer MUST compare capability fingerprints, authority results, audit events, and ledger/provenance hashes.

### P7-009 — P8 readiness package

Before P7 exit, a draft P8 pilot charter MUST specify exactly one venture, one authority class, one operating window, numeric exposure and loss ceilings, named approvers, monitoring, stop conditions, and rollback authority.

### P7-010 — Human exit decision

P7 exits only through a named human decision recorded as ACCEPTED, BLOCKED, PARTIAL, or NOT EXECUTED. Tests and manifests alone cannot close P7.

## 3. Prohibitions

P7 MUST NOT:

- attach a real CEO;
- create or use live credentials;
- contact an external party;
- execute real capital, payment, customer, deployment, broker, network, venture, or worker actions;
- enable P8;
- widen any authority boundary;
- treat synthetic or isolated evidence as live evidence;
- use model output as approval;
- skip the P7 entry or exit gate.

## 4. Required evidence

P7 evidence MUST include:

- baseline reconciliation against P6.5;
- topology and deployment rehearsal;
- backup/restore and corruption evidence;
- alert and incident drill evidence;
- credential custody and revocation evidence;
- complete 81-case authority rehearsal matrix;
- normal and injected-failure results for recovery controls;
- full regression and focused test reports;
- P8 pilot charter;
- technical/non-technical certification report;
- independent review and human exit decision.

## 5. Exit interpretation

A passing P7 result means only that the project is ready to seek separate approval for P8. It does not authorize live action, real credentials, or production deployment.

## 6. Change control

Changes to execution class, authority fields, rehearsal matrix, test threshold, evidence-retention rule, or exit requirements require a new P7 policy revision and impact analysis.
