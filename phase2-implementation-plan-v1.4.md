# Autonomous Venture Agent — Phase 2 Implementation Plan

## v1.4

**Status:** P2.2 implemented; awaiting delegated analyst/auditor acceptance
**Phase:** P2 — Opportunity and thesis system
**Governing specification:** `phase2-policy-spec-v1.0.md`
**Predecessor:** `phase1-implementation-plan-v1.1.md`
**Execution class:** Shadow reasoning, synthetic integration, and evidence production only

## 1. Implementation rules

1. Preserve all P0/P1 authority, provenance, recovery, and evidence invariants.
2. Do not modify historical P0/P1 artifacts in place.
3. Keep P2 acceptance separate from venture formation, capital, payment, and
   external-action authority.
4. Preserve typed evidence and raw inputs through every transformation.
5. Every increment produces technical evidence and an operator-readable
   non-technical assessment.
6. No real CEO, real capital, live broker, payment, venture, or worker action
   is permitted in P2.

## 2. Increment registry

| Increment | Scope | Required evidence | Exit |
|---|---|---|---|
| P2.0 | Baseline and contracts | Source hashes, schemas, fixtures, authority review | Contracts reviewed |
| P2.1 | Opportunity intake | Idempotent intake, provenance envelope, source typing, negative tests | Intake certified |
| P2.2 | Evidence normalization | Taint-preserving normalization, contradiction handling, raw-input retention | Evidence boundary certified |
| P2.3 | Thesis identity | Fingerprint, similarity, resubmission, cooldown, duplicate tests | Identity certified |
| P2.4 | Scoring and lifecycle | Deterministic scoring, review decisions, accept/reject/expire/quarantine transitions | Lifecycle certified |
| P2.5 | Replay and adversarial checks | Replay from durable state, tamper/cross-scope/authority-denial tests | Replay certified |
| P2.6 | P2 certification | Full P2 report, human review, P3 entry decision | P2 exit recorded |

## 3. Ordered implementation guidance

### P2.0 — Baseline and contracts

Record the P1 exit commit, P0/P1 hashes, execution classes, and inherited
forbidden transitions. Define versioned schemas for the P2 interfaces before
implementing lifecycle behavior.

### P2.1 — Opportunity intake

Accept only typed opportunity envelopes with stable idempotency keys. Preserve
source references and hashes without storing secrets. Prove duplicate delivery
converges to one durable intake record.

### P2.2 — Evidence normalization

Normalize evidence without discarding the raw envelope or its provenance.
Preserve source type, taint, freshness, contradictions, and transformation
history. Attempted instruction smuggling must remain evidence, not authority.

### P2.3 — Thesis identity

Implement the thesis fingerprint and material-similarity rules. Demonstrate
that copy, price, or channel changes alone cannot evade cooldown or duplicate
handling.

### P2.4 — Scoring and lifecycle

Implement deterministic scoring with versioned weights and explicit uncertainty.
Exercise acceptance, rejection, expiration, quarantine, and supersession. Prove
that no accepted thesis reaches a venture, capital, payment, or broker path.

### P2.5 — Replay and adversarial checks

Destroy in-memory state and replay decisions from durable records. Test
tampered evidence, stale evidence, cross-portfolio access, duplicate requests,
authority widening, and contradictory source handling.

### P2.6 — Certification

Produce a technical/non-technical certification report with exact commands,
source hashes, per-increment evidence, negative tests, limitations, and a human
P3 entry decision. Preserve all raw evidence and keep the P2 denominator
separate from the P1 ADV-001–ADV-049 denominator.

## 4. Required artifacts

P2 must produce versioned policy and implementation documents, schemas,
migrations where needed, ADRs, fixtures, tests, certification runner, raw
evidence, certification report, evidence manifest, status record, and rollback
or quarantine runbook.

## 5. Current next action

Conduct delegated analyst/auditor acceptance of the pushed P2.2 artifacts.
Verify the seven exit-criteria tests, normalized-evidence contracts, monotonic
taint, contradiction isolation, append-only lineage, raw-envelope immutability,
freshness, scope, and instruction-smuggling containment. Implementation remains
bounded by the entry gate and cannot create venture or external-action authority.
