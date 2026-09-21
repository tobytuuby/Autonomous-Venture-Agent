# Autonomous Venture Agent — Remaining Phases Implementation Plan

## v1.1-DRAFT — Review Remediation

**Status:** Draft for review; planning artifact only.  
**Supersedes for review:** `remaining-phases-implementation-plan-v1.0-DRAFT.md`  
**Roadmap:** `project-phase-plan-v2.1-DRAFT.md`  
**Starting boundary:** P6.5 accepted at `P6.5-ACCEPTED`.  
**Authorization:** This plan does not authorize P7 implementation, live credentials, or external action.

## 1. Common increment contract

Every increment must provide:

- exact source/configuration hashes and clean-tree state;
- focused tests with a declared denominator;
- full regression with a declared denominator;
- all required negative and unauthorized-action tests;
- at least one normal-path and one injected-failure result for each applicable control;
- raw evidence location and reproducibility command;
- technical and non-technical certification;
- named independent reviewer for readiness, degraded-mode, and expansion claims.

**Minimum pass rule:** zero failing required tests, zero unauthorized actions, zero unexplained authority widening, and zero unexplained ledger/provenance drift. Warnings require explicit disposition.

## 2. P7 — Production readiness

### P7.0 — Baseline and scope lock

Reconcile P6.5 evidence, verify no P7 implementation exists, freeze the scope, and create the P7 evidence manifest.

**Pass:** exact P6.5 hashes match; worktree is clean; all nine live authorities remain denied; no P7 code path is active.

### P7.1 — Production topology and deployment controls

Define production-shaped topology, ownership, configuration separation, release, rollback, and deployment-denial behavior.

**Pass:** two consecutive clean rehearsal runs; deployment rollback succeeds; no secret or live side effect appears.

### P7.2 — Backup, restore, and disaster recovery

Test authoritative-state backup, integrity verification, restore, corruption rejection, service loss, and host-loss recovery.

**Pass:** one normal restore and one injected-failure restore pass; restored hashes match expected state; corrupted backup is rejected; recovery objectives are recorded.

### P7.3 — Observability and incident response

Verify audit events, metrics, alerts, retention, incident severity, escalation, and evidence preservation.

**Pass:** every required alert is triggered and acknowledged in the test; every incident class has a runbook; evidence is preserved within 15 minutes in rehearsal.

### P7.4 — Credential and provider-boundary readiness

Verify kernel-owned custody, rotation, revocation, allowlisting, redaction, dependency pinning, and fail-closed behavior using synthetic or isolated fixtures only.

**Pass:** rotation and revocation each pass normal and failure-injected cases; secret-leak tests are clean; no real production credential is used.

### P7.5 — Complete live-boundary rehearsal

Exercise all nine live-authority fields across this matrix:

| State | Required coverage |
|---|---|
| Request | denied and recorded |
| Approval | unauthorized or missing approval rejected |
| Dispatch | blocked before external side effect |
| Response | synthetic/isolated response classified |
| Reconciliation | mismatch detected and blocks |
| Failure | retry/terminal classification deterministic |
| Freeze | new action blocked |
| Revoke | grant/capability removed and recorded |
| Quarantine/wind-down | state isolated, evidence preserved, recovery path recorded |

**Pass:** 9 fields × 9 states covered; every denial and mismatch test passes; at least one injected failure per state family; zero real external effects.

### P7.6 — Independent readiness certification

Run the full P7 matrix and full repository regression. Review residual risks, pilot limits, staffing, stop conditions, and P8 charter.

**P7 exit:** all P7 tests pass; no unauthorized action; required evidence is complete; P8 charter is numeric and written; independent reviewer recommends ACCEPTED; human entry decision is recorded.

## 3. P8 — Limited live pilot

P8 requires an approved pilot charter before implementation. The charter must name exactly one venture, one authority class, one operating window, a numeric exposure ceiling, a numeric loss ceiling, approvers, monitoring, and automatic stop conditions.

### P8.0 — Final preflight
Validate the charter, credentials, limits, reconciliation, monitoring, and stop paths.

### P8.1 — First controlled live action
Perform only the smallest approved action through a kernel-owned service.

### P8.2 — Live monitoring and reconciliation
Classify drift as zero, tolerated, or blocking. Any unexplained authority, ledger, provenance, credential, or customer-state drift is blocking. Preserve evidence within 15 minutes and freeze on blocking drift.

### P8.3 — Freeze, revoke, recovery, and wind-down
Exercise approved stop paths where safe; otherwise use an approved simulation with an explicit limitation. No unsafe test may be represented as a live proof.

### P8.4 — Pilot certification
A pilot passes only with zero unapproved actions, complete reconciliation, passed stop controls, and human residual-risk acceptance.

## 4. P9 — Controlled expansion and hardening

Allowed expansion dimensions, in order, are:

1. venture count;
2. authority class;
3. exposure ceiling;
4. operating window;
5. provider/dependency;
6. concurrency.

Only one dimension may change per increment. Each increment requires before/after capability fingerprints, authority-denial tests, ledger/provenance comparison, an independent reviewer, and a rollback threshold.

### P9.0 — Expansion baseline
Freeze accepted P8 state and choose one dimension and numeric limit.

### P9.1 — Reliability and degraded mode
Inject provider outages, delayed/duplicate responses, operator loss, database failover, and degraded mode. The independent reviewer compares authority fingerprints before and after; any unexpected capability or authority change fails the increment.

### P9.2 — Incremental expansion
Apply one approved dimension only; verify rollback and stop conditions.

### P9.3 — Audit and control sampling
Sample 100% of live authority changes and financial reconciliation events, plus at least 10 randomly selected ordinary operational events per approved operating day. Any unexplained sample failure blocks the increment.

### P9.4 — Expansion certification
Confirm limits, attribution, isolation, provenance, reconciliation, and recovery remain intact.

## 5. P10 — General production

### P10.0 — Operating model
Assign service owners, approvers, on-call roles, incident responsibility, and audit responsibility.

### P10.1 — Recurring controls
Use the default cadence unless a stricter policy applies:

- daily: financial and reconciliation controls;
- weekly: authority, configuration, and anomaly controls;
- monthly: recovery, access, and credential review;
- after every incident or material change: targeted recertification.

### P10.2 — Change and release governance
Require impact analysis, tests, staged rollout, rollback, approval, and post-release verification.

### P10.3 — Go-live review
Review all evidence, limitations, operating readiness, suspension authority, and residual-risk acceptance.

### P10.4 — Steady-state acceptance
Record the production scope, numeric limits, control cadence, first post-go-live audit date, and automatic suspension conditions.

## 6. Forbidden shortcuts

No P7 code, live credential, external action, P8 pilot, P9 expansion, or P10 production activity may begin while this plan is a draft or before the applicable entry decision.

## 7. Required entry package

Before P7 starts, the repository must contain approved versions of:

1. roadmap v2.1;
2. this implementation plan v1.1;
3. P7 policy specification v1.0;
4. P7 status record;
5. P7 test/certification matrix;
6. explicit P7 entry decision.

P7 remains blocked until all six exist and are approved.
