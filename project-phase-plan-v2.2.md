# Autonomous Venture Agent — Project Phase Roadmap

## v2.2 — Post-P11 Review and Limited-Test Proposal

**Status:** Canonical, approved on 2026-09-29.
**Approval record:** docs/reviews/PROJECT-ROADMAP-v2.2-approval.md
**Supersedes for review:** `project-phase-plan-v2.1.md`
**Supersedes for current phase tracking:** `project-phase-plan-v1.4.md`
**Last canonical plan before v2.2 approval:** `project-phase-plan-v1.4.md`
**Baseline:** `main` at `c554fc2e4786a6725354013e525b02ed7c9149a4`
**Planning authorization:** User authorization on 2026-09-29 to plan and revise the roadmap for P12–P14.
**P12 exit requirement:** An independent audit decision is mandatory.

## 1. Purpose and status

This proposal reconciles the project roadmap with accepted P0–P11 work and defines the proposed gates before any possible limited production test. It does not authorize production readiness, a live test, a production deployment, or any external action.

P11 is accepted and merged for its synthetic, non-authorizing planning-gate scope. Its `READY_FOR_INDEPENDENT_REVIEW` result validates proposal completeness only. P11 does not assess a real system or authorize the proposal it validates.

This revision records authorization for **roadmap planning only**. It does not authorize P12 implementation, P13 execution, live authority, or P14 operations. Each phase still requires its own explicit entry decision.

## 2. Current operating boundary

Until a separate, exact test charter has completed P12 and a separate execution authorization is recorded for P13:

- execution remains static, synthetic, shadow, or isolated;
- all nine live authorities and all action indicators remain denied;
- no real CEO, worker, venture, customer, provider, credential, or production target is attached or activated;
- no customer, capital, payment, broker, deployment, network, credential, provider, worker, venture, or external action is performed;
- model output cannot authorize or widen execution;
- P11 acceptance is not production readiness or test approval;
- P12 audit acceptance is necessary for progression but is not itself execution authorization;
- P13 and P14 remain proposed and unauthorized.

Any proposal that exceeds its separately approved scope is blocked. This roadmap grants no default authority and sets no real target, budget, data access, or test window.

## 3. Phase map

| Phase | Name | Status | Boundary and exit |
|---|---|---|---|
| P0 | Policy kernel and certification | Complete for P0 scope | Kernel and synthetic certification foundation |
| P1 | CEO shadow hardening and Gate 2 closure | Complete for P1 scope | Shadow reasoning; no CEO execution authority |
| P2 | Opportunity and thesis system | Complete for P2 scope | No venture launch or capital action |
| P3 | Venture formation and sandboxing | Complete for defined scope | Synthetic-only |
| P4 | Venture execution and operations | Complete for defined scope | Synthetic recording/operations boundaries |
| P5 | Revenue, treasury, and financial operations | Complete for defined scope | Synthetic financial operations only |
| P6 | Portfolio operations and shared services | Accepted through P6.5 | Synthetic portfolio operations |
| P7 | Runtime boundaries and synthetic certification | Complete for defined scope | No live authority; certification only |
| P8 | Synthetic pilot certification and closeout | Accepted through P8.4 | Synthetic certification only |
| P9 | Synthetic boundary hardening | Accepted | Synthetic-only; all live authorities denied |
| P10 | Synthetic governance rehearsal | Accepted | No production readiness or live authority |
| P11 | Production-readiness planning gate | Accepted and merged | Non-authorizing validator; `READY_FOR_INDEPENDENT_REVIEW` only |
| P12 | Exact test charter and readiness evidence review | Roadmap planning authorized; phase entry and implementation not authorized | Ends only with an independent audit decision of ACCEPTED or BLOCKED for the exact charter and evidence |
| P13 | Bounded limited-test execution | Proposed; not authorized | May begin only after P12 ACCEPTED, a separate exact user authorization, and all operational prerequisites; must remain within that charter |
| P14 | Independent post-test review and disposition | Proposed; not authorized | Independent review decides ACCEPTED, BLOCKED, or STOP; no automatic continuation or expansion |

No later phase is implied by this map. Any expansion or steady-state operation requires a separately authorized roadmap change and its own phase gates.

## 4. P12 — Exact test charter and readiness evidence review

### Objective

Prepare one exact, reviewable proposal for a possible limited test and independently decide whether the proposal and its supporting evidence meet the approved P12 criteria. P12 is a planning and audit phase. It performs no production test and no external action.

### Required charter content

The charter must bind, at minimum:

- one exact objective and measurable success criteria;
- the target identity and environment, recorded in a controlled manner;
- the venture/tenant and data classification;
- every proposed operation and the exact allowed authority for each operation;
- explicit denied operations and all nine live-authority states;
- duration, concurrency, exposure/loss bounds, and any applicable limits;
- pre-start approvals, operator responsibilities, monitoring signals, and alert handling;
- automatic stop thresholds, manual stop authority, containment, rollback/recovery, and rehearsal evidence;
- evidence collection, integrity protection, retention, incident reporting, and post-test review;
- source/configuration versions and hashes, test denominator, exclusions, and reproducible commands;
- residual risks, assumptions, legal/security/operational review, and the exact decision requested.

The initial P12 work must use synthetic fixtures and must not connect to or inspect a production target. If a proposed test requires any real data, customer contact, capital, payment, broker execution, deployment, network access, credentials, provider calls, worker/venture execution, or other external effect, the charter must identify it explicitly for review. This roadmap does not grant it.

### Independent audit and mandatory exit

P12 cannot close on implementer self-review, a passing test count, or a manifest alone. A reviewer independent of the charter author and implementation must inspect the exact charter, criteria, source/configuration bindings, raw evidence, denominators, negative tests, safeguards, stop/recovery plan, authority matrix, and residual risks.

The reviewer must issue a signed or otherwise attributable decision tied to the exact charter hash and reviewed source commit:

- **ACCEPTED:** the charter package meets P12 criteria and may be submitted for a separate P13 execution decision. This is not permission to execute.
- **BLOCKED:** P12 remains open; findings, evidence, and remediation requirements are recorded. No P13 entry is allowed.

**P12 exit is the recorded independent audit decision.** Absence of the decision, unbound evidence, reviewer conflict, unexplained failure, hash mismatch, or unresolved authority/safety finding means P12 is BLOCKED.

P12 requires its own versioned policy, implementation plan, test/evidence plan, test denominator, acceptance criteria, and entry decision before implementation begins. The denominator must be fixed in those artifacts before tests are run; this roadmap does not invent a count.

## 5. P13 — Bounded limited-test execution

P13 remains proposed and unauthorized. No P13 work or execution starts solely from this roadmap or from P12 ACCEPTED.

P13 may be considered only after:

1. P12 is ACCEPTED by its independent audit;
2. the exact charter is unchanged and its hashes still match;
3. the user gives separate explicit authorization naming the exact test and permitted operations;
4. required operational, security, legal, and service-owner approvals are recorded;
5. monitoring, stop controls, containment, rollback/recovery, operator coverage, and evidence capture are ready and independently checked.

Any eventual P13 specification must define the precise runtime authority and test surface. Anything outside the charter triggers immediate stop, preserved evidence, and review. Model output cannot authorize a step, exception, retry, or scope change.

## 6. P14 — Independent post-test review and disposition

P14 is proposed only for a future test that was separately authorized and completed or stopped. It must reconcile planned versus actual scope, authority events, monitoring, stops, incidents, exposure, data handling, recovery, evidence integrity, and success criteria.

An independent reviewer must issue an attributable ACCEPTED, BLOCKED, or STOP disposition against the exact P13 charter and evidence. A positive P14 decision closes only the reviewed test. It does not authorize expansion, another test, or steady-state operation.

## 7. Cross-phase invariants and stop rules

- All nine live authorities remain denied unless a later, separately reviewed phase and exact user authorization explicitly allow a narrowly stated operation.
- Authority is least-privilege, time-bounded, target-bound, and revocable; no phase grants ambient or reusable authority.
- No real CEO is attached, and no worker or venture execution authority is enabled by this roadmap.
- Model output is advisory data and never approval, a credential, or an execution instruction.
- Synthetic evidence is never relabeled as production evidence.
- Missing, stale, conflicting, or unverifiable evidence fails closed.
- Any unexplained scope or authority drift blocks entry or stops an active authorized test.
- Stop, quarantine, rollback, and recovery behavior must be rehearsed within the permitted test boundary before P13 entry.
- No P12 ACCEPTED result can override a P13 prerequisite or grant authority.

## 8. Change control and next decisions

This approved v2.2 is the current canonical roadmap. The prior v1.4 plan and v2.1 draft remain unchanged for historical traceability; the v2.2 review draft is also retained unchanged.

Roadmap approval authorizes no phase implementation or live activity. P12 implementation is not authorized. The next P12 gate requires submission of the exact proposed charter for independent audit; any P12 implementation requires separate explicit user authorization. P12 exit still requires the independent ACCEPTED or BLOCKED audit decision bound to the exact charter hash and reviewed source. P13 requires separate exact execution authorization after P12 ACCEPTED; P14 requires a separate entry decision after P13 ends.

## 9. Changelog

- **v2.2 approved (2026-09-29):** Reconciles the phase map through accepted P11; establishes P12 exact charter and readiness evidence review, P13 bounded limited-test execution, and P14 independent post-test review as proposed gated phases. Makes an independent audit decision a mandatory P12 exit condition. Approval does not authorize implementation or live execution.
