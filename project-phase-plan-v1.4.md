# Autonomous Venture Agent — Project Phase and Implementation Plan

## v1.4

**Status:** Canonical project plan version v1.4; supersedes v1.3 for current phase tracking. This document does not replace
`phase0-policy-kernel-spec-v11.md`, `phase0-implementation-plan-v3.2.md`,
or either historical v10/v3.1 document.

**Purpose:** Define the full project after the current Phase 0 policy-kernel work,
including the order of operations, implementation increments, evidence gates,
authority boundaries, and conditions for any graduated external action.

**Current repository point:** P0.16 is implemented through a synthetic,
red-team-only treasury-to-payment path. P1 Gate 2 is closed by explicit human
review recorded on 2026-09-18. The provider evidence remains classified as
externally configured but independently unverifiable; closure records the human
acceptance decision and does not create a cryptographic provider attestation.
P2.0–P2.3 are accepted; P2.4 requirements are reviewed and implementation is authorized. No real capital action is enabled.

---

## 1. Document topology and phase-level change control

The project is governed by a master phase registry plus an independent document
set for every phase. The master document does not absorb the detailed content
of a phase and does not become a second implementation plan.

### 1.1 Master project documents

The master set contains:

- `project-phase-plan-v1.0.md`: phase order, dependencies, cross-phase gates,
  status, current document versions, and the project-wide transition rules.
- `project-phase-plan-v1.1.md`: historical P1-to-P2 transition record; retained unchanged.
- `project-phase-plan-v1.0-DRAFT.md`: this review artifact; it is not
  canonical until approved.
- `docs/PROJECT_STATUS.md`: current phase, open gates, active risks, and
  links to the exact phase artifacts in use.

### 1.2 Per-phase documents

Each phase receives its own versioned set:

| Artifact | Example | Purpose |
|---|---|---|
| Governing specification | `phase1-policy-spec-v1.0.md` | What must be true; requirements, invariants, interfaces, and prohibitions |
| Implementation plan | `phase1-implementation-plan-v1.0.md` | What gets built, in what order, and what evidence closes each increment |
| Status record | `docs/PHASE1_STATUS.md` | Current state, evidence, blockers, and decision history |
| ADRs | `docs/ADR-P1-*.md` | Material phase-specific design decisions |
| Schemas/migrations | `schemas/*`, `migrations/*` | Machine-readable contracts and authoritative state changes |
| Tests/certification report | `tests/phase1/*` plus `docs/reports/PHASE1-*.md` | Machine evidence and the technical/non-technical certification assessment |
| Raw evidence inputs | Reports, manifests, logs, hashes, and replay artifacts referenced by the report | Reproducible source material; not a substitute for the report |

P0 remains the naming exception because its governing documents already exist:
`phase0-policy-kernel-spec-v11.md` and
`phase0-implementation-plan-v3.2.md`. They are referenced by the master
registry rather than renamed.

### 1.3 Phase document structure

Every phase specification and implementation plan follows the P0 pattern:

1. status and version;
2. source documents and exact hashes;
3. objective and scope;
4. requirement registry;
5. interfaces and data contracts;
6. security and authority invariants;
7. ordered implementation increments;
8. test and evidence mapping;
9. exit gate;
10. forbidden shortcuts;
11. changelog and supersession record.

A phase may have multiple implementation-plan revisions while it is active.
The governing specification changes only when requirements or invariants
change. An implementation correction that does not alter requirements still
increments the implementation-plan version and records the reason.

### 1.4 Current-phase and future-phase updates

- **Active phase update:** create a new version of that phase's specification or
  implementation plan; never rewrite the prior version. Update its status
  record and the master registry only after validation.
- **Future phase update:** edit or replace its Draft/Proposed documents without
  changing the active phase or claiming future exit evidence.
- **Cross-phase change:** record an impact analysis in the master registry,
  identify every affected phase, version each affected artifact, and rerun
  the impacted dependency gates.
- **Historical artifact:** immutable and retained for traceability.
- **Canonical artifact:** the currently approved version for that phase.
- **Active artifact:** the canonical version currently being implemented.
- **Superseded artifact:** replaced by a newer approved version but retained
  for history.

No phase may be marked Canonical or Active merely because its documents exist.
The phase status is promoted only by an explicit review decision and a passing
entry gate from the predecessor phase.

### 1.5 Certification-report standard

Tests, manifests, logs, and replay outputs are technical evidence inputs. The
phase-exit artifact is a certification report that interprets those inputs for
both engineers and decision-makers. A report must contain:

**Technical assessment**

- exact source, test, schema, migration, and configuration versions/hashes;
- environment and execution identity;
- commands or runner entry points used;
- scope, test universe, denominator, and exclusions;
- per-test or per-scenario results;
- failure, retry, crash-recovery, and negative-test results;
- unauthorized-action and side-effect findings;
- raw evidence locations and reproducibility instructions;
- known gaps, nondeterminism, and limitations.

**Non-technical assessment**

- what the phase was intended to prove;
- what the results mean in operational and governance terms;
- what the results do not prove;
- residual risks and affected stakeholders;
- whether the phase is PASS, CLAIMED, BLOCKED, PARTIAL, or NOT EXECUTED;
- required human decision, approval, or remediation;
- explicit recommendation to enter, remain in, or exit the phase.

The report must keep these sections distinct while connecting every conclusion
to technical evidence. A summary manifest alone cannot close a phase, and a
passing unit-test count cannot be presented as proof of a broader operational
or governance claim. When evidence is externally configured but not independently
verifiable, the report must say so explicitly rather than label the phase PASS.

---

## 2. Project operating model

The project is built as a sequence of gated phases. A later phase may not
weaken an earlier invariant, bypass the capability broker, or convert synthetic
evidence into production evidence by relabeling it.

Every phase must produce:

- a phase-specific implementation record;
- machine-checkable tests and fixtures;
- an evidence manifest naming source versions and hashes;
- explicit negative tests for forbidden transitions;
- a rollback, quarantine, or hard-stop procedure;
- an exit decision recorded by a human operator.

The system has four distinct execution classes:

| Class | Meaning | Permitted before production approval |
|---|---|---|
| Static/unit | Pure code and deterministic fixtures | Yes |
| Synthetic integration | Recording transports, test credentials, test ventures, red-team identities | Yes |
| Shadow reasoning | A model may analyze but cannot execute or authorize external effects | Yes, after its gate |
| Graduated external action | Real provider, real account, or real capital action | Only after the project-wide production gate |

The CEO, Venture Managers, and workers are venture-intelligence roles. They
never receive direct shell, browser, filesystem, generic execution, credential,
payment, or deployment capabilities. They interact through the broker and
kernel-owned services only.

---

## 3. Phase map

| Phase | Name | Governing specification | Implementation plan | Status | Entry dependency | External action |
|---|---|---|---|---|---|---|
| P0 | Policy kernel and certification | Existing v11 | Existing v3.2 | Complete for P0 scope | Repository baseline | Static/unit and synthetic integration only |
| P1 | CEO Stage 0 shadow hardening and Gate 2 closure | `phase1-policy-spec-v1.0.md` | `phase1-implementation-plan-v1.1.md` | Complete for P1 scope | P0 Gate 1, P0.15 shadow foundation, and explicit Gate 2 review | Shadow reasoning only |
| P2 | Opportunity and thesis system | `phase2-policy-spec-v1.0.md` | `phase2-implementation-plan-v2.1.md` | Active / Implementation | P1 exit, P2 approval, P2.0/P2.1 acceptance, and P2.2 review recorded in phase status records | None |
| P3 | Venture formation and sandboxing | `phase3-policy-spec-v1.0.md` | `phase3-implementation-plan-v1.0.md` | Future / Not started | P2 exit | Synthetic only |
| P4 | Venture execution and operations | `phase4-policy-spec-v1.0.md` | `phase4-implementation-plan-v1.0.md` | Future / Not started | P3 exit | Synthetic only |
| P5 | Revenue, treasury, and financial operations | `phase5-policy-spec-v1.0.md` | `phase5-implementation-plan-v1.0.md` | Future / Not started | P4 exit | Synthetic, then gated test integration |
| P6 | Portfolio operations and shared services | `phase6-policy-spec-v1.0.md` | `phase6-implementation-plan-v1.0.md` | Future / Not started | P5 exit | Synthetic only until P7 |
| P7 | Graduated external operation | `phase7-policy-spec-v1.0.md` | `phase7-implementation-plan-v1.0.md` | Future / Not started | P6 exit plus independent production review | Limited and reversible |
| P8 | Production hardening and scale | `phase8-policy-spec-v1.0.md` | `phase8-implementation-plan-v1.0.md` | Future / Not started | P7 pilot exit | Only within approved limits |

P0 is the current foundation. P1–P6 must preserve the P0 invariants.
P7 is the first phase where any real external action may be considered.
P8 is not a license to remove controls; it is the scale and operations phase
for controls that have already survived P7.

The phase-map action descriptions map to the execution classes as follows:

| Phase-map wording | Execution class |
|---|---|
| Static/unit and synthetic integration only | Static/unit and synthetic integration |
| Shadow reasoning only | Shadow reasoning |
| None | No external action; static/unit or synthetic integration only |
| Synthetic only | Synthetic integration |
| Synthetic, then gated test integration | Synthetic integration; no graduated external action |
| Synthetic only until P7 | Synthetic integration; graduated external action remains blocked |
| Limited and reversible | Graduated external action, under the P7 pilot gate |
| Only within approved limits | Graduated external action, after P7 approval and P8 controls |


---

## 4. Phase charters and phase-plan boundaries

The master document defines only phase charters, dependencies, boundaries, and
exit gates. Numbered implementation increments belong in each phase's separate
implementation-plan file listed in the phase map.

### P0 — Policy kernel and certification

**Objective:** Establish the authoritative state, identity boundary, capability
broker, governors, provenance, recovery, kill switch, lifecycle fixtures,
shadow CEO runtime, bootstrap treasury, and certification gates.

**Governing documents:**

- `phase0-policy-kernel-spec-v11.md`
- `phase0-implementation-plan-v3.2.md`
- historical v10/v3.1 documents remain read-only history.

**Charter boundary:** P0 owns the policy kernel and its synthetic certification
foundation. P0.15 supplies the initial CEO shadow plumbing and P0.16 supplies
the synthetic treasury-to-payment composition. P0 does not claim that external
Gate 2 calls are independently verified.

**Exit conditions:**

- ADV-001–ADV-049: 49/49 with zero unauthorized actions.
- BOOT-001–BOOT-006: PASS.
- RealPaymentAdapter: adapter-enforced $5–$20 aggregate exposure and explicit
  CEO/Venture-Manager denial.
- P0.16 composed path: synthetic red-team only.
- Gate 1 is complete; Gate 2 was closed by explicit human review on 2026-09-18 and remains limited to shadow evidence.
- Stage 1 remains blocked.

### P1 — CEO Stage 0 shadow hardening and Gate 2 closure

**Objective:** Complete and independently assess the shadow CEO boundary without
granting the CEO execution authority.

**Relationship to P0.15:** P0.15 already delivered the initial CEO agent,
provider wiring, shadow runner, decision logging, tool-list fingerprinting, and
the committed Gate 2 manifest/report. P1 does not relabel or redo that work.
P1 treats it as the baseline implementation, hardens the missing evidence and
durable-state behavior, and closes only the gaps that remain after P0.15.

**Charter boundary:** P1 owns shadow-mode completion and evidence quality. It
does not spawn Venture Managers or workers, grant execution capabilities, or
enable Stage 1 capital actions.

**Exit gate:**

- The 49-case suite is rerun against the exact configuration.
- ADV-040 is rerun against durable CEO state.
- Evidence proves the configured provider was actually reached, without storing
  API secrets.
- All shadow decisions remain non-executing.
- No Venture Manager or worker is spawned by the CEO.
- A technical/non-technical certification report records the result and any
  remaining limitations.
- The P1 exit decision is recorded by a human operator.

**Recorded exit:** P1 is complete for its defined scope. Gate 2 was explicitly
classified **CLOSED** by the project operator on 2026-09-18. The evidence class
remains “externally configured but independently unverifiable”; no real CEO,
capital, payment, broker, venture, worker, or external action was used.

### P2 — Opportunity and thesis system

**Objective:** Give the CEO a bounded, evidence-producing way to discover,
compare, reject, and retain business opportunities without launching them.

**Charter boundary:** P2 owns opportunity, evidence, thesis, scoring, review,
cooldown, expiration, and replay contracts. Detailed increments belong in
`phase2-implementation-plan-v1.0.md`.

**Exit gate:**

- A thesis can be accepted, rejected, expired, or quarantined deterministically.
- No thesis can create a venture or request capital directly.
- Tainted evidence cannot become trusted merely through summarization.
- Every decision is replayable from stored evidence and policy versions.

### P3 — Venture formation and sandboxing

**Objective:** Convert an approved thesis into an isolated test venture with a
bounded Venture Manager and certified worker archetypes.

**Charter boundary:** P3 owns venture identity, namespace, sandbox, manager
envelope, worker archetypes, provisioning, teardown, recovery, wind-down, and
cross-venture visibility boundaries. Detailed increments belong in
`phase3-implementation-plan-v1.0.md`.

**Exit gate:**

- Two or more test ventures operate concurrently without data or authority
  leakage.
- Managers cannot self-escalate, spawn outside their archetypes, or access
  another venture's state.
- Destroyed containers reconstruct from authoritative state.
- Wind-down revokes grants, quarantines outputs, and preserves audit evidence.

### P4 — Venture execution and operations

**Objective:** Execute bounded venture work through managers and workers while
keeping all side effects behind kernel services.

**Charter boundary:** P4 owns task packets, research/build workflows, compute
and spend requests, operational limits, incident handling, repair, quarantine,
recovery, metrics, and cost attribution. Detailed increments belong in
`phase4-implementation-plan-v1.0.md`.

**Exit gate:**

- All work is attributable to a venture, role, grant, and task packet.
- Workers cannot convert output into authority or credentials.
- Repairs cannot widen authority or conceal prohibited changes.
- Recovery and kill-switch tests pass during active task execution.

### P5 — Revenue, treasury, and financial operations

**Objective:** Connect venture economics to authoritative financial state without
removing the financial governor or exposing payment credentials to agents.

**Charter boundary:** P5 owns ledger reconciliation, revenue and settlement
events, refunds, fees, chargebacks, treasury policy integration, adapter
hardening, profit sweeps, ratchets, reserves, and human approval for future
external payment boundaries. Detailed increments belong in
`phase5-implementation-plan-v1.0.md`. P0.16 remains the existing synthetic
bootstrap/payment baseline; P5 integrates and extends it rather than silently
claiming a production payment path.

**Exit gate:**

- Financial state is authoritative, durable, idempotent, and reconcilable.
- No agent has banking or payment credentials.
- Synthetic end-to-end flows pass failure, retry, crash, and ratchet tests.
- Real payment remains disabled until the P7 gate explicitly authorizes it.

### P6 — Portfolio operations and shared services

**Objective:** Operate multiple ventures as a portfolio while preserving
venture isolation and evidence-gated shared capabilities.

**Charter boundary:** P6 owns portfolio registry and reporting, CEO-to-manager
coordination, shared-service demand evidence, stateless shared execution,
aggregate anomaly controls, harvest, reinvestment, quarantine, wind-down, and
portfolio audit. Detailed increments belong in
`phase6-implementation-plan-v1.0.md`.

**Exit gate:**

- Shared services are provisioned only from kernel-verified demand.
- Aggregate controls detect slow-drift and cross-counterparty structuring.
- One venture can be quarantined without taking unrelated ventures offline.
- Portfolio decisions remain explainable and replayable.

### P7 — Graduated external operation

**Objective:** Introduce narrowly scoped real integrations only after the
complete kernel, shadow, venture, financial, and portfolio gates have passed.

**Charter boundary:** P7 owns production-readiness review, isolated real
provider adapters, human-approved micro-capital, progressive exposure, live
reconciliation, kill-switch rehearsal, rollback, and a single-venture pilot.
Detailed increments belong in `phase7-implementation-plan-v1.0.md`.

**Exit gate:**

- Human approval is required for the first live action and each authority or
  exposure increase.
- Credentials are held by kernel-owned services, never agents.
- Freeze, revoke, reconcile, recover, and wind-down paths pass during the pilot.
- A failed live control closes the pilot and returns the system to P6 or P5.

### P8 — Production hardening and scale

**Objective:** Scale only the controls and operating patterns proven in P7.

**Charter boundary:** P8 owns high-availability state, backup/restore,
separation of duties, continuous policy and dependency review, capacity,
provider-failure engineering, independent audit sampling, and controlled
expansion. Detailed increments belong in
`phase8-implementation-plan-v1.0.md`.

**Exit gate:**

- Scale increases are incremental, reversible, and separately approved.
- Governance evidence remains complete under concurrency and failure.
- No production convenience path bypasses the broker, ledger, governors, or
  kill switch.

---

## 5. Cross-phase gates

The following gates apply regardless of phase numbering:

1. **Authority gate:** the requested action is within the actor's role,
   venture, capability, and current policy.
2. **Evidence gate:** the evidence is attributable, fresh enough, and not
   incorrectly promoted from tainted or synthetic state.
3. **Financial gate:** exposure, reserves, aggregate windows, beneficiary,
   structuring, and ratchet rules all pass.
4. **Execution gate:** the action uses an approved kernel-owned adapter with
   bounded credentials, idempotency, timeout, and reconciliation.
5. **Recovery gate:** crash, retry, duplicate, quarantine, wind-down, and
   hard-stop behavior are tested for the affected action class.
6. **Human gate:** any new real-world side effect, increased exposure, new
   beneficiary class, or authority expansion receives explicit human approval.
7. **Evidence-preservation gate:** the phase cannot close on a summary manifest
   alone; raw per-case records, hashes, and decision/review records must be
   retained.

---

## 6. Required artifact set for every phase

Each phase must add or update, without overwriting historical artifacts:

- phase specification or architecture addendum;
- implementation plan with numbered increments;
- ADRs for material design choices;
- schemas and migration records;
- unit, integration, adversarial, crash-recovery, and negative tests;
- certification runner and raw machine evidence;
- a certification report containing both the technical assessment and the
  non-technical assessment defined in §1.5;
- evidence manifest with source hashes and configuration fingerprints, cited by
  the report rather than treated as the report itself;
- status record with explicit PASS, CLAIMED, BLOCKED, PARTIAL, or NOT EXECUTED
  states;
- rollback and operator runbook.

A phase document may not use “PASS” to mean “mechanism exists” when the
phase's acceptance criterion requires an exercised end-to-end scenario. The
certification report must distinguish technical test success from the broader
decision about whether the phase is safe, complete, and authorized to advance.

---

## 7. Versioning and historical preservation

- P0 v11 and P0 plan v3.2 remain historical inputs to this project plan.
- Any correction to v3.2 itself must be a new version, not an in-place rewrite.
- This document is `v1.0-DRAFT` until the full phase map and gates are reviewed.
- Approved revisions increment the project-plan version and record a changelog.
- No historical v10, v3.1, or earlier artifact may be overwritten.

---

## 8. Immediate next work

P1 exit and Gate 2 closure are recorded in the v1.1 transition record. P2 approval
is recorded in the v1.2 transition record. P2.5 acceptance is recorded in the
P2-005 acceptance record. P2 remains bounded by the P2 charter and inherited
P0/P1 invariants.

1. Conduct the P2.6 certification requirements review and implementation
   planning, preserving the separate P2 denominator and all raw evidence.
2. Continue only with the ordered P2.6 certification work; P2 exit and P3 entry
   require explicit human review and must not be inferred from test counts.
3. Preserve the `/49` P1 evidence and do not relabel it as P2 evidence.
4. Keep CEO execution authority, Venture Manager/worker spawning, payments,
   capital actions, and all P7 real integrations blocked.
