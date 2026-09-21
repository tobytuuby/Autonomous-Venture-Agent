# Autonomous Venture Agent — Remaining Phases Implementation Plan

## v1.0-DRAFT

**Status:** Draft for review; planning artifact only.  
**Roadmap:** `project-phase-plan-v2.0-DRAFT.md`  
**Starting boundary:** P6.5 accepted at tag `P6.5-ACCEPTED`.  
**Implementation status:** No P7 work is authorized by this document alone.

## 1. Purpose

This plan defines the work required after P6.5 in the order required to reach general production. It prevents implementation of isolated future features outside an adopted roadmap. Each phase must receive explicit entry approval, use a phase-specific branch or change set, produce its required evidence, and close through human review before the next phase begins.

The plan preserves the project-wide invariants:

- synthetic and live evidence remain separate;
- all nine live-authority fields remain denied until the applicable approved gate;
- agents never receive direct network, broker, payment, credential, deployment, customer, capital, venture, or worker authority;
- model output never authorizes an external action;
- all financial activity remains synthetic until an approved P8 pilot;
- every live exposure increase is separately approved, bounded, reversible, and auditable.

## 2. Phase sequence and approval state

| Phase | Implementation package | Entry condition | Primary result | Exit decision |
|---|---|---|---|---|
| P7 | Readiness and pre-production controls | P6.5 accepted; roadmap and P7 specification approved | Production-shaped readiness without real effects | P7 readiness certification |
| P8 | Limited live pilot | P7 accepted; pilot charter and live-action approval signed | One bounded, reversible live pilot | Pilot acceptance or rollback |
| P9 | Controlled expansion and hardening | P8 accepted; expansion decision approved | Broader operation within ratcheted limits | Expansion certification |
| P10 | General production governance | P9 accepted; production decision approved | Normal production operation and recurring governance | Go-live/steady-state acceptance |

## 3. Common increment contract

Every increment must produce:

- implementation commit and clean-tree record;
- exact source and configuration hashes;
- focused tests and full regression result;
- negative tests for prohibited authority;
- failure, retry, crash, recovery, and rollback evidence where applicable;
- technical certification report;
- non-technical assessment of authority, risk, limitations, and residual dependencies;
- updated status record;
- explicit human decision.

A test count is not sufficient to prove operational readiness or live safety.

## 4. P7 implementation plan — production readiness

### P7.0 — Baseline reconciliation and scope lock

Reconcile the accepted P6.5 artifacts, current repository state, existing invariants, and roadmap. Record the exact P6.5 parent, accepted tag, manifest hash, open warnings, and all deferred items. Confirm that no P7 implementation exists in the baseline.

**Evidence:** baseline manifest, repository status, dependency map, and scope decision.

### P7.1 — Production topology and deployment controls

Define and test the production-shaped topology, service ownership, configuration separation, release process, rollback mechanism, and deployment-denial behavior. Use synthetic or isolated environments only.

**Evidence:** topology record, deployment runbook, configuration fingerprint, rollback rehearsal, and denial tests.

### P7.2 — Backup, restore, and disaster recovery

Exercise authoritative-state backup, restore, integrity verification, point-in-time recovery assumptions, corrupted-backup rejection, and recovery after service or host loss.

**Evidence:** recovery test matrix, restored-state hashes, corruption tests, recovery-time measurements, and limitations.

### P7.3 — Observability and incident response

Implement or verify structured audit events, metrics, alerts, audit retention, operator dashboards, incident severity, escalation, evidence preservation, and post-incident procedures.

**Evidence:** alert tests, incident drill, audit-retention check, escalation record, and operator runbook.

### P7.4 — Credential and provider-boundary readiness

Verify kernel-owned credential custody, rotation, revocation, provider allowlisting, secret redaction, endpoint identity, dependency pinning, and fail-closed behavior. No real production credential is used as P7 evidence.

**Evidence:** custody design, rotation/revocation rehearsal, secret-leak tests, provider-denial tests, and configuration fingerprints.

### P7.5 — Live-boundary rehearsal

Exercise production-shaped adapters with synthetic or isolated fixtures. Rehearse approval, dispatch, response, reconciliation, freeze, revoke, quarantine, wind-down, and rollback. Prove that every real-authority path remains disabled.

**Evidence:** end-to-end rehearsal report, authority-denial matrix, recovery traces, and no-side-effect certification.

### P7.6 — Independent readiness certification

Run the complete P7 test and evidence inventory. Review residual risks, staffing, operating hours, stop conditions, pilot limits, and the proposed P8 pilot charter.

**P7 exit criteria:**

- all P7 increments accepted or explicitly dispositioned;
- no unauthorized external action;
- recovery, rollback, freeze, revoke, quarantine, and wind-down pass;
- production-shaped configuration is reproducible and secret-free;
- P8 pilot scope and exposure ceilings are written;
- independent human review records P7 as ACCEPTED.

P7 acceptance does not authorize real external action.

## 5. P8 implementation plan — limited live pilot

P8 may not begin without a separate written live-action approval naming the venture, authority class, exposure limit, duration, operators, stop conditions, and rollback authority.

### P8.0 — Pilot authorization and final preflight

Validate the pilot charter, human approvers, service ownership, credentials, exposure limits, monitoring, reconciliation, and stop conditions. Confirm that only the named authority is enabled.

### P8.1 — First controlled live action

Perform the smallest permitted live action through a kernel-owned service. Record request identity, approval identity, policy/configuration hashes, provider response, resulting state, and reconciliation result.

### P8.2 — Live monitoring and reconciliation

Observe the pilot under the approved window. Reconcile external state to internal ledgers, detect drift, preserve evidence, and halt on any mismatch or policy violation.

### P8.3 — Freeze, revoke, recovery, and wind-down rehearsal

Exercise or safely simulate the approved stop paths, including credential revocation, capability withdrawal, quarantine, rollback where possible, recovery, and venture wind-down.

### P8.4 — Pilot certification

Determine whether the pilot is accepted, extended only by a new approval, rolled back, or blocked.

**P8 exit criteria:**

- no unapproved action or exposure;
- all live actions attributable to a human approval and kernel-owned service;
- reconciliation is complete and independently reviewable;
- stop, revoke, recovery, and wind-down evidence passes;
- residual risk is accepted by the named human authority.

## 6. P9 implementation plan — controlled expansion and hardening

### P9.0 — Expansion baseline

Freeze the accepted P8 configuration and establish the next exposure ceiling, venture limit, authority scope, and rollback threshold.

### P9.1 — Reliability and degraded-mode hardening

Test provider outages, delayed responses, duplicate responses, partial failures, operator loss, database failover, and degraded-mode behavior without widening authority.

### P9.2 — Incremental expansion

Add only one approved dimension at a time: venture, authority, exposure, provider, or operating window. Each change requires its own approval and evidence record.

### P9.3 — Independent audit and control sampling

Perform recurring evidence sampling, ledger reconciliation, access review, configuration comparison, anomaly review, and incident-drill verification.

### P9.4 — Expansion certification

Confirm that scale has not weakened attribution, isolation, governors, kill switch, provenance, or recovery.

**P9 exit criteria:**

- all approved expansion steps are reversible;
- reliability and degraded-mode tests pass;
- audit sampling finds no unexplained authority or ledger drift;
- production limits and on-call ownership are documented;
- human review accepts P9.

## 7. P10 implementation plan — general production and steady-state governance

### P10.0 — Production operating model

Assign service owners, approvers, on-call roles, release authorities, incident responsibilities, audit responsibilities, and review cadence.

### P10.1 — Continuous control system

Establish recurring certification for policy, identity, capability, financial reconciliation, provenance, recovery, anomaly controls, credentials, and live-authority boundaries.

### P10.2 — Change and release governance

Require impact analysis, test evidence, staged rollout, rollback plan, approval, and post-release verification for every material change.

### P10.3 — Production go-live review

Review all P0–P10 evidence, unresolved limitations, operating readiness, residual risk, rollback, incident response, and authority limits. Confirm that go-live is bounded by written policy rather than implied by successful tests.

### P10.4 — Steady-state acceptance

Record the production decision, effective limits, review cadence, first post-go-live audit date, and conditions that automatically suspend operation.

**P10 exit criteria:**

- production owners and on-call coverage are active;
- recurring controls are scheduled and evidenced;
- rollback and suspension authority is explicit;
- current evidence supports the approved operating scope;
- residual risks are accepted;
- human review records **GENERAL PRODUCTION ACCEPTED**.

## 8. Forbidden shortcuts

The following actions are prohibited while this plan is only a draft:

- beginning P7 implementation;
- creating P8 live credentials or enabling live authorities;
- treating P6.5 evidence as production evidence;
- implementing P9/P10 features ahead of their phase;
- using a model response as approval;
- increasing exposure without a new approval record;
- weakening or renaming the nine live-authority denials;
- deleting or rewriting historical evidence;
- skipping a phase exit because focused tests pass.

## 9. Required artifacts before P7 entry

Before P7 can start, the repository must contain approved versions of:

1. the complete roadmap;
2. the P7 governing policy specification;
3. this remaining-phase implementation plan, or a superseding adopted plan;
4. P7 status record;
5. P7 test and certification matrix;
6. explicit P7 entry decision.

P8, P9, and P10 require their own governing specifications before their respective entry gates.

## 10. Change control

Changes to phase scope, authority boundary, execution class, exposure limits, exit criteria, or go-live definition require a new implementation-plan revision and impact analysis against the roadmap. This draft is not permission to execute live or financial actions.
