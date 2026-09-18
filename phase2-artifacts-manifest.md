# Phase 2 Artifact Manifest

**Document:** P2 Opportunity and Thesis System artifact manifesto  
**Status:** Adopted as a condition of P2 implementation approval  
**Adoption date:** 2026-09-18  
**Governing specification:** `phase2-policy-spec-v1.0.md`  
**Active implementation plan:** `phase2-implementation-plan-v2.0.md`
**Execution class:** Shadow reasoning, synthetic integration, and evidence production only

## 1. Purpose

This manifest makes the P2 required artifact set concrete. It identifies the
intended path, format, owning increment, and acceptance criteria for every
artifact required by the P2 policy specification and implementation plan.

The P2 increments are adopted as an ordered sequence:

`P2.0 → P2.1 → P2.2 → P2.3 → P2.4 → P2.5 → P2.6`

An increment may not be skipped, reordered, or marked complete solely because a
later increment produces related evidence. Each increment requires its own
technical evidence and operator-readable non-technical assessment before the
next increment begins.

## 2. Artifact registry

| Artifact | Intended path and format | Owner increment | Acceptance criteria |
|---|---|---|---|
| P2 policy specification | `phase2-policy-spec-v1.0.md` | P2.0 baseline | Approved requirements, interfaces, authority invariants, entry/exit gates, and forbidden shortcuts are preserved. |
| P2 implementation plan | `phase2-implementation-plan-v1.1.md` | P2.0 baseline | Ordered increments, evidence obligations, limitations, and P2.0 next action are versioned and approved. |
| P2 status record | `docs/PHASE2_STATUS.md` | P2.0 and each increment | Records approval, current increment, source hashes, evidence class, decisions, blockers, and human review. |
| Versioned schemas | `schemas/p2/*.json` or equivalent machine-readable format | P2.0 | Opportunity, EvidenceEnvelope, ThesisFingerprint, ThesisScore, ReviewDecision, LifecycleTransition, and ReplayRequest contracts validate required identity, provenance, policy/configuration, actor, scope, correlation, and idempotency fields. No secrets or direct capabilities are permitted. |
| P2 migrations | `migrations/p2/*.sql` | P2.0/P2.1 as needed | Durable structures are additive/versioned, idempotent, scope-aware, and preserve append-only evidence and transition history. If no migration is needed, P2.0 records that determination and its rationale. |
| P2 ADRs | `docs/ADR-P2-*.md` | Owning increment | Each material design choice records context, decision, alternatives, consequences, authority impact, provenance impact, and rollback/quarantine implications. |
| Synthetic fixtures | `tests/p2/fixtures/*` | P2.0–P2.5 | Fixtures cover valid, duplicate, contradictory, stale, tainted, tampered, cross-scope, and authority-denial cases without secrets or real external identities. |
| Increment tests | `tests/p2/test_*.py` and/or project-native test format | P2.0–P2.5 | Tests cover positive behavior, negative behavior, idempotency, persistence, crash/recovery where applicable, and zero unauthorized external actions for the owning increment. |
| P2 certification runner | `tests/certification/p2_certify.py` | P2.6 | Runs the complete P2 test/evidence set, preserves the P2 denominator separately from P1 ADV-001–ADV-049, emits deterministic machine-readable results, and records failures without relabeling them as passes. |
| Raw P2 evidence | `tests/certification/p2-raw/*` | P2.0–P2.6 | Retains commands, outputs, hashes, fixtures, per-case results, replay records, and failure details needed to reproduce the certification claims. |
| P2 evidence manifest | `tests/certification/p2-manifest.json` | P2.6 | Names all source versions, schema/configuration fingerprints, test universe, denominator, raw evidence paths, hashes, exclusions, and execution limitations. |
| P2 certification report | `docs/reports/PHASE2-CERTIFICATION.md` | P2.6 | Separates technical and non-technical assessments; includes exact commands, per-increment results, negative tests, replay adversarial results, taint-preservation proofs, residual risk, evidence classification, and the P3 entry recommendation. |
| Replay adversarial report | Section of `docs/reports/PHASE2-CERTIFICATION.md` plus raw records under `tests/certification/p2-raw/replay/` | P2.5/P2.6 | Demonstrates durable-state replay, tamper detection, stale/contradictory evidence handling, cross-portfolio denial, duplicate handling, exact commands, and expected failures. |
| Taint-preservation evidence | Section of `docs/reports/PHASE2-CERTIFICATION.md` plus raw records under `tests/certification/p2-raw/taint/` | P2.2/P2.6 | Shows external, synthetic, inferred, and operator evidence remain separately typed and tainted through normalization, scoring, lifecycle, and replay. |
| Rollback/quarantine runbook | `docs/runbooks/PHASE2-ROLLBACK-QUARANTINE.md` | P2.5/P2.6 | Defines deterministic quarantine, replay, correction, rollback, evidence preservation, operator review, and hard-stop procedures without deleting history or widening authority. |
| Human decision records | `docs/PHASE2_STATUS.md` and increment decision records under `docs/reviews/P2-*.md` | P2.0–P2.6 | Each material transition records reviewer identity, timestamp, decision, rationale, evidence references, limitations, and explicit approval or rejection. |

## 3. Increment ownership and exit conditions

### P2.0 — Baseline and contracts

Produces the approved baseline record, source hashes, inherited forbidden
transitions, schemas, migration determination, authority-review fixtures, and
the P2.0 human decision record. Exit requires contract review and proof that
the contracts cannot grant venture, worker, capital, payment, broker, or
external-action authority.

### P2.1 — Opportunity intake

Produces typed intake fixtures, durable idempotency behavior, provenance
envelopes, source typing, duplicate-delivery tests, and the P2.1 decision
record. Exit requires duplicate convergence and negative tests for untyped or
unauthorized intake.

### P2.2 — Evidence normalization

Produces raw-envelope retention, normalized evidence, taint and contradiction
fixtures, transformation history, instruction-smuggling tests, and taint
evidence. Exit requires proof that normalization cannot promote evidence into
authority.

### P2.3 — Thesis identity

Produces deterministic fingerprints, material-similarity fixtures, duplicate
linkage, cooldown/resubmission behavior, and identity tests. Exit requires
proof that changing copy, price, or channel alone cannot bypass identity rules.

### P2.4 — Scoring and lifecycle

Produces versioned scoring configuration, explainable score records, review
decisions, lifecycle transition fixtures, and authority-denial tests. Exit
requires deterministic accept/reject/expire/quarantine/supersede behavior and
proof that accepted theses cannot reach venture, capital, payment, or broker
paths.

### P2.5 — Replay and adversarial checks

Produces durable-state replay records, tamper/stale/contradictory evidence
tests, cross-portfolio denial tests, duplicate-request tests, authority-
widening tests, and the rollback/quarantine runbook. Exit requires replay
reproduction and expected failure for tampered or unauthorized inputs.

### P2.6 — Certification

Produces the complete technical/non-technical certification report, evidence
manifest, raw evidence index, human decision records, and explicit P3 entry
decision. Exit requires human review of the report and all limitations; it does
not occur automatically from a passing test count.

## 4. Zero-venture-authority condition

P2 implementation is approved only for opportunity, evidence, thesis, scoring,
review, cooldown, expiration, quarantine, and replay contracts.

P2 must contain zero code paths that instantiate a Venture Manager or worker,
launch a venture, allocate capital, execute a payment, call a live broker,
request credentials, contact a counterparty, or perform another external
action. This condition must be testable through static inspection, negative
tests, authority-denial tests, and certification evidence. A model proposal,
accepted thesis, score, or review decision is never authorization for any such
action.

## 5. Required certification sections

The P2.6 report must include, as distinct sections:

1. Technical assessment.
2. Non-technical assessment.
3. Replay Adversarial Test Report.
4. Taint Preservation Evidence.
5. Human Decision Audit Trail.
6. Authority and side-effect assessment.
7. Evidence classification and limitations.
8. P3 entry recommendation and explicit human decision.

P1's `ADV-001`–`ADV-049` denominator and Gate 2 evidence remain P1
evidence. P2 certification must use and report its own denominator.

