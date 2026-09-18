# Autonomous Venture Agent — Phase 2 Policy Specification

## v1.0

**Status:** Approved for implementation; P2 active
**Phase:** P2 — Opportunity and thesis system
**Predecessor:** P1 complete for defined scope; Gate 2 explicitly closed on 2026-09-18
**Execution class:** Shadow reasoning, synthetic integration, and evidence production only

## 1. Objective and scope

P2 establishes the bounded opportunity and thesis system used to discover,
compare, reject, retain, expire, quarantine, and replay business opportunities.
It creates evidence and decisions; it does not launch ventures, allocate capital,
spawn Venture Managers or workers, execute payments, or perform external
actions.

P2 inherits every P0 and P1 authority, provenance, recovery, kill-switch,
financial, and evidence invariant. A P2 artifact cannot relabel synthetic or
externally configured evidence as independently verified.

## 2. Requirements

- **OPP-001 — Opportunity identity:** Every opportunity has a stable,
  collision-resistant identity and an immutable source/provenance envelope.
- **OPP-002 — Evidence typing:** External, synthetic, inferred, and operator
  evidence are typed separately; taint and provenance survive transformation,
  summarization, and replay.
- **OPP-003 — Thesis fingerprint:** Every thesis records category, customer
  segment, core offer, monetization model, acquisition channel, assumptions,
  and a deterministic fingerprint.
- **OPP-004 — Deterministic lifecycle:** An opportunity/thesis can be received,
  under review, accepted, rejected, expired, quarantined, or superseded only
  through a kernel-validated transition.
- **OPP-005 — Explainable scoring:** Scores are deterministic for a fixed
  evidence set, policy version, and configuration; each score records inputs,
  weights, uncertainty, and reviewer-visible reasons.
- **OPP-006 — Review boundary:** Acceptance is a portfolio-analysis decision,
  not authorization to launch a venture, spend money, contact a counterparty,
  or request credentials.
- **OPP-007 — Similarity and resubmission:** Materially duplicate theses are
  linked to prior records and subject to cooldown/resubmission rules; changing
  copy, price, or channel alone does not bypass identity rules.
- **OPP-008 — Expiration and quarantine:** Stale, contradictory, unsafe, or
  policy-invalid evidence can expire or quarantine a thesis without deletion of
  its audit history.
- **OPP-009 — Replayability:** A decision is reproducible from durable evidence,
  source hashes, policy/configuration versions, and the decision algorithm.
- **OPP-010 — Isolation and authority:** P2 records are scoped to the owning
  portfolio context and cannot widen model, tool, budget, venture, worker,
  payment, or capital authority.
- **OPP-011 — Human decision record:** P2 entry, exit, material policy changes,
  and any promotion from candidate to accepted thesis require an explicit
  operator-review record.
- **OPP-012 — Evidence-preservation:** Raw inputs, normalized envelopes,
  transformations, score outputs, and lifecycle transitions are append-only or
  versioned; corrections never erase prior evidence.

## 3. Interfaces and data contracts

P2 will define versioned contracts for Opportunity, EvidenceEnvelope,
ThesisFingerprint, ThesisScore, ReviewDecision, LifecycleTransition, and
ReplayRequest. Contracts must include identity, provenance, policy version,
configuration fingerprint, timestamps, actor/role, venture scope where
applicable, and correlation/idempotency identifiers.

No contract may contain provider secrets or grant direct external capabilities.

## 4. Security and authority invariants

The CEO remains shadow-only. P2 cannot create a Venture Manager or worker
identity, call a payment or broker adapter, allocate capital, launch a venture,
or convert a model proposal into an authorized action. Tainted evidence cannot
become trusted solely because a model summarized it. All consequential
transitions remain kernel/broker controlled.

## 5. Entry gate

P2 entry requires:

- P1 status and Gate 2 closure recorded;
- P0/P1 documents and hashes preserved;
- P1 evidence classification retained;
- no production CEO or external-action authority enabled;
- a reviewed P2 plan and implementation checklist.

## 6. Exit gate

P2 exits only when:

- lifecycle transitions are deterministic and negative-tested;
- provenance and taint survive ingestion, normalization, scoring, and replay;
- duplicate/similar thesis handling and cooldown rules are exercised;
- accepted theses cannot launch ventures or request capital;
- replay reproduces the decision from durable state;
- technical and non-technical certification reports are reviewed by a human;
- the P3 entry decision is explicitly recorded.

## 7. Forbidden shortcuts

Do not treat opportunity acceptance as venture approval, use untyped web/provider
content as instructions, bypass the kernel or broker, delete contradictory
evidence, widen authority through scoring, or begin P3 work under a P2 result.

## 8. Change control

Requirement or invariant changes require phase2-policy-spec-v1.1.md or later.
Implementation corrections that preserve requirements belong in a new P2
implementation-plan version.
