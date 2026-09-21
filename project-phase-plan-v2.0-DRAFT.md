# Autonomous Venture Agent — Complete Project Roadmap

## v2.0-DRAFT

**Status:** Draft for review; not canonical until explicitly approved.  
**Supersedes:** `project-phase-plan-v1.0.md` only after approval.  
**Purpose:** Establish one complete, authoritative sequence from the accepted P6.5 synthetic portfolio boundary through controlled live operation and general production. No future phase is implementation-authorized merely because it appears in this document.

## 1. Current project boundary

Phases P0 through P5 are complete for their approved synthetic or shadow scopes. Phase 6 is complete through P6.5.

P6.5 acceptance evidence:

- Evidence commit/tag target: `89b2399291a48393c6ec3b1092b3b202e3fbfe68`
- Acceptance metadata commit: `ba8b8ff777617f33c06caed3c5a8fe328908a31d`
- Tag: `P6.5-ACCEPTED`
- Remote `main`: `ba8b8ff`
- Manifest SHA-256: `705d7f25af163e47903408a08fe51b24f8e2b82268ec6b2d83d7743fcbf13563`
- Evidence: focused 12/12; combined P6.0–P6.5 116/116; full repository 337/337
- Known limitation: six pre-existing SQLite `ResourceWarning` messages remain documented; no tests failed.

**Current state:** P6.5 accepted. P7 has not started. All live authorities and external effects remain disabled.

## 2. Project-wide execution classes

| Class | Meaning | Permitted before P8 approval |
|---|---|---|
| Static/unit | Deterministic code and fixture validation | Yes |
| Synthetic integration | Test ventures, test identities, recording-only transports, simulated financial activity | Yes |
| Shadow reasoning | Model analysis with no execution authority | Yes, when separately approved |
| Pre-production rehearsal | Production-shaped deployment and recovery tests using synthetic or isolated credentials | Yes, after P7 entry approval |
| Controlled live pilot | Narrow, human-approved real integration with reversible limits | Only during P8 |
| Expanded production | Approved real operation within ratcheted limits | Only during P9/P10 |

Synthetic evidence must never be relabeled as live evidence. A phase exit is a human decision supported by technical and non-technical certification evidence.

## 3. Complete phase map

| Phase | Name | Purpose | External action | Status |
|---|---|---|---|---|
| P0 | Policy kernel and certification | Establish policy, identity, capability, financial, provenance, recovery, and certification foundations | None; synthetic only | Complete |
| P1 | CEO shadow hardening and Gate 2 closure | Harden and assess the shadow CEO boundary | Shadow only | Complete |
| P2 | Opportunity and thesis system | Discover, evaluate, retain, reject, and replay opportunities | None | Complete |
| P3 | Voyage scout / venture formation | Form bounded synthetic ventures and preserve sandbox isolation | Synthetic only | Complete |
| P4 | Venture factory recording-only | Record venture creation, lifecycle, and operational decisions | Recording-only | Complete |
| P5 | Revenue and ledger systems | Establish synthetic revenue, reconciliation, treasury simulation, and human review ledgers | Synthetic only | Complete |
| P6 | Portfolio and shared services | Coordinate multiple ventures, shared services, anomaly controls, quarantine, and portfolio certification | Synthetic only | Complete through P6.5 |
| P7 | Production readiness and controlled-integration preparation | Prove operational readiness, deployment/recovery controls, live-boundary design, and pre-production rehearsals | No real external effects | Not started |
| P8 | Limited live pilot | Introduce one narrowly scoped, reversible live integration under explicit human approval | Limited and reversible | Not started |
| P9 | Controlled expansion and production hardening | Expand only after pilot evidence; harden availability, recovery, monitoring, and governance | Approved limits only | Not started |
| P10 | General production and steady-state governance | Establish ordinary production operation with continuing gates, audit, and rollback | Approved production operation | Not started |

**Go-live definition:** The system is not considered generally live at P7 or P8. General production readiness is achieved only after the P10 exit gate. P8 is a controlled pilot; P9 is controlled expansion and hardening.

## 4. Remaining-phase charters

### P7 — Production readiness and controlled-integration preparation

P7 prepares the system for live evaluation without performing real external actions.

Scope:

- production topology and deployment runbooks;
- backup, restore, disaster recovery, and rollback;
- observability, alerting, audit retention, and incident response;
- dependency and provider failure handling;
- credential custody and rotation design;
- live-authority adapter contracts using isolated/pre-production fixtures;
- kill-switch, revoke, quarantine, wind-down, and reconciliation rehearsals;
- separation of duties and human approval workflow;
- final P8 pilot charter and exposure ceilings.

Exit requirement: independent review confirms that the system can enter a limited pilot without bypassing the kernel, broker, governors, ledgers, provenance, or kill switch. P7 does not authorize live action.

### P8 — Limited live pilot

P8 permits the first real external activity only under a written pilot approval.

Scope:

- one approved venture or use case;
- one approved authority at a time;
- minimal exposure and explicit loss limits;
- kernel-owned credentials and service boundaries;
- human approval before each live action or approved action batch;
- real-time or bounded-latency reconciliation;
- immediate freeze and rollback procedures;
- pilot stop conditions and return to synthetic/P7 operation.

Exit requirement: the pilot demonstrates safe execution, reconciliation, recovery, revocation, and wind-down under real conditions. Any control failure blocks expansion and returns the system to the prior safe boundary.

### P9 — Controlled expansion and production hardening

P9 increases coverage only after P8 acceptance.

Scope:

- additional ventures or approved authority classes;
- incremental exposure increases using ratchets;
- high-availability and capacity controls;
- provider outage and degraded-mode operation;
- independent audit sampling;
- continuous policy, dependency, and configuration review;
- operational staffing, on-call, and incident exercises;
- tested rollback from every expansion step.

Exit requirement: the expanded system remains attributable, reversible, reconciled, fail-closed, and auditable under concurrency, failure, and operator turnover.

### P10 — General production and steady-state governance

P10 establishes the normal production operating model.

Scope:

- formal production service ownership;
- recurring certification and control testing;
- change management and release gates;
- access reviews, credential rotation, and separation-of-duties reviews;
- financial and operational reconciliation;
- ongoing anomaly, quarantine, and wind-down governance;
- incident reporting and post-incident remediation;
- documented limits for any future authority expansion.

Exit requirement: production operation is approved by human review with current evidence, explicit residual-risk acceptance, tested rollback, and an active governance cadence. P10 does not remove any P0–P6 invariant.

## 5. Cross-phase gates

Every remaining phase must close all applicable gates:

1. **Predecessor gate:** predecessor phase is accepted and its artifacts are immutable.
2. **Scope gate:** phase specification and implementation plan are approved before implementation.
3. **Authority gate:** execution class and permitted authorities are explicit.
4. **Evidence gate:** denominator, commands, environment, hashes, failures, retries, and limitations are recorded.
5. **Safety gate:** negative tests prove forbidden authority paths remain unavailable.
6. **Recovery gate:** freeze, revoke, quarantine, restore, rollback, and wind-down are exercised.
7. **Human decision gate:** a named reviewer records PASS, BLOCKED, PARTIAL, or NOT EXECUTED.
8. **Transition gate:** the next phase cannot start until the prior exit decision and entry conditions are recorded.

For P8–P10, the following additional gates apply:

- live action must be separately approved from technical readiness;
- exposure increases require a new decision record;
- a live pilot failure automatically blocks expansion;
- real credentials remain kernel-owned and inaccessible to agents;
- no model output can authorize a live action by itself.

## 6. Required document set

Before P7 implementation begins, the repository must contain and approve:

- this roadmap revision;
- the remaining-phase implementation plan;
- a governing policy specification for each remaining phase;
- a phase status record;
- phase-specific ADRs where needed;
- test and certification plans;
- pilot and production approval templates.

The remaining-phase implementation plan is planning authority only. It does not itself authorize P7, P8, P9, or P10 implementation.

## 7. Change control

A change to phase order, execution class, authority boundary, go-live definition, exposure limits, or exit criteria requires a new roadmap revision. Historical versions remain preserved. No phase may be skipped, merged informally, or started solely because implementation work appears useful.

## 8. Current decision

- P6.5: **ACCEPTED**
- P7: **NOT STARTED; separately gated**
- P8–P10: **PROPOSED; not authorized**
- Real CEO attachment: **disabled**
- Real capital, payment, customer, deployment, credential, broker, venture, worker, and network authorities: **disabled**
