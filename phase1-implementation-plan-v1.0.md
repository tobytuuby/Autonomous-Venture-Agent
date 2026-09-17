# Autonomous Venture Agent — Phase 1 Implementation Plan

## v1.0

**Status:** Draft for review
**Phase:** P1 — CEO Stage 0 shadow hardening and Gate 2 closure
**Governing specification:** `phase1-policy-spec-v1.0.md`
**Baseline:** P0.15 implementation in `phase0-implementation-plan-v3.2.md`
**Execution class:** Shadow reasoning only
**Explicitly excluded:** real CEO attachment, Venture Manager or worker spawning, external payments, live broker execution, and real capital actions.

## 1. Implementation rules

1. Preserve P0.15 as historical and executable baseline; extend it with new P1 increments.
2. Keep `ADV-001`–`ADV-049` as the only ADV certification denominator: `/49`.
3. Keep BOOT, P0.13, P0.16, and provider-boundary checks separately labeled; they do not inflate or replace `/49`.
4. Every increment produces a technical/non-technical report, not only a manifest.
5. Any evidence that depends on an externally configured endpoint MUST be labeled “externally configured but not independently verifiable” unless the report contains independently verifiable execution evidence.
6. Do not store secrets or attach a real CEO.

## 2. Increment registry

| Increment | Scope | Required technical evidence | Required non-technical evidence | Exit |
|---|---|---|---|---|
| P1.0 | Baseline and configuration inventory | P0.15 file/hash inventory; secret-free configuration fingerprint; dependency graph | Scope confirmation; authority boundary; known limitations | Baseline reconciled |
| P1.1 | Provider boundary hardening | Adapter contract tests; request metadata redaction; endpoint/model/prompt/tool hashes; negative secret tests | Provider provenance; explanation of what is and is not independently verifiable | Boundary certified |
| P1.2 | Durable shadow decision state | Idempotent decision state machine; append-only/tamper-evident log; duplicate retry tests | Recovery responsibilities; operator-readable state meanings; failure escalation rules | Durable state certified |
| P1.3 | Crash recovery and replay | Interrupted-run recovery; container/process restart test; deterministic replay; CEO-shaped `ADV-040` | Recovery runbook; residual-risk statement; human review of recovery assumptions | Recovery certified |
| P1.4 | Gate 2 evidence closure | Real configured endpoint rerun or explicit unverified classification; raw 49-entry report; no synthetic substitution | Independent review decision; evidence provenance; limitations and external dependencies | Gate 2 classified and reviewable |
| P1.5 | Reachability and shadow-boundary certification | Red-team denial of payment, treasury, broker execution, venture spawn, and worker paths; full `ADV-001`–`ADV-049` rerun | Sign-off that no execution authority was granted; rollback/hold decision | P1 exit report complete |

## 3. Detailed implementation guidance

### P1.0 — Baseline and configuration inventory

- Record the exact parent commit and P0.15 artifacts under test.
- Enumerate provider endpoint origin, model name, prompt hash, tool-list hash, policy versions, and runner/runtime versions without recording credentials.
- Identify every path from CEO input to broker, finance, payment, venture launch, worker, and shared-service code.
- Record whether each dependency is static/unit, synthetic integration, shadow reasoning, or externally configured.

### P1.1 — Provider boundary hardening

- Keep all model calls behind the existing provider interface.
- Add secret-redacting request/response metadata suitable for independent review.
- Reject missing or mismatched configuration fingerprints.
- Ensure provider errors and partial responses reach a durable terminal classification.
- Test that the CEO cannot select an unapproved provider, model tier, endpoint, or tool list through natural-language output.
- Retain raw evidence only where it is safe and necessary; otherwise retain hashes and redacted envelopes.

### P1.2 — Durable shadow decision state

- Define states for received, dispatched, response-recorded, replayable, completed, rejected, and quarantined.
- Use a stable idempotency key derived from scenario, run, and configuration identity.
- Make duplicate requests converge on one terminal decision record.
- Ensure a process retry cannot duplicate an external call record or create a second decision.
- Preserve prior committed records; corrections append a new record.

### P1.3 — Crash recovery and replay

- Interrupt the runner at pre-dispatch, post-dispatch, and post-response checkpoints.
- Recover solely from durable state and the configuration fingerprint.
- Re-run `ADV-040` against a CEO-shaped shadow identity with durable portfolio/ledger fixtures.
- Demonstrate that conversational history is neither required nor trusted for recovery.
- Produce a replay artifact that another reviewer can execute without secrets.

### P1.4 — Gate 2 evidence closure

- Run the exact 49 ADV scenarios against the exact configured provider boundary where authorized and available.
- Preserve the `/49` denominator and include one raw result for each ID.
- Include a provider execution trace, or explicitly classify the run as externally configured but not independently verifiable.
- Never label a synthetic transport as real-model evidence.
- Record the human review decision and whether Gate 2 is closed, conditionally accepted, or remains open.

### P1.5 — Reachability and shadow-boundary certification

- Run red-team-only denial tests for `RealPaymentAdapter`, `BootstrapTreasury`, live payment, live broker execution, venture launch, workers, and shared services.
- Re-run the full `ADV-001`–`ADV-049` suite and report exactly `49/49` or the precise failing/not-executable set.
- Verify no P1 change creates a production CEO identity or grants execution capabilities.
- Publish the technical/non-technical P1 certification report and update project status only after review.

## 4. Certification report contract

The P1 certification report MUST include:

- commit under test and dirty-tree status;
- increment-by-increment results;
- technical test commands and raw outputs or linked artifacts;
- non-technical assessment of authority, provenance, operator impact, limitations, and residual risk;
- ADV result table containing all 49 IDs and preserving the `/49` denominator;
- provider configuration classification;
- secret-handling statement;
- independent reviewer decision;
- explicit open items and the decision on P1 exit.

A manifest may support the report but cannot replace it.

## 5. Definition of done

P1 is complete only when:

- all P1 policy requirements are implemented or explicitly dispositioned;
- every claimed result has reproducible evidence;
- the raw ADV report contains 49 entries and no denominator drift;
- crash recovery and `ADV-040` are demonstrated against durable CEO-shaped state;
- red-team reachability denial is demonstrated;
- the report separates technical pass/fail from non-technical readiness;
- no real CEO or real capital action was used;
- Gate 2 is either independently closed or clearly remains open with its reason recorded.

## 6. Change control

Changes to scope, increments, evidence classes, denominator, or authority boundaries require `phase1-implementation-plan-v1.1.md` or later. This file is not permission to execute external or financial actions.
