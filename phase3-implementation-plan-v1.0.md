# Autonomous Venture Agent — Phase 3 Implementation Plan

## v1.0

**Status:** P3.0 active; baseline-and-contracts review pending  
**Phase:** P3 — Venture formation and sandboxing  
**Governing specification:** phase3-policy-spec-v1.0.md  
**Predecessor:** phase2-implementation-plan-v2.3.md  
**Execution class:** Synthetic integration and shadow reasoning only

## 1. Implementation rules

1. Preserve all P0/P1/P2 authority, provenance, recovery, taint, and evidence invariants.
2. Keep P3 evidence separate from P2's 41-test denominator and P1's ADV-001–049 denominator.
3. Use only synthetic identities, recording transports, test namespaces, and non-routable or disabled network modes.
4. Do not create real ventures, managers, workers, credentials, capital, payments, broker calls, customer contact, deployments, or external actions.
5. Every increment produces machine-checkable evidence and an operator-readable assessment.

## 2. Increment registry

| Increment | Scope | Required evidence | Exit |
|---|---|---|---|
| P3.0 | Baseline and contracts | Source hashes, five schemas, fixtures, negative tests, ADR, review record | Contracts accepted |
| P3.1 | Venture identity and namespace | Deterministic identity, scope checks, duplicate/cross-scope tests | Identity certified |
| P3.2 | Sandbox provisioning | Synthetic provisioning, image/config fingerprint, idempotency, no-network tests | Provisioning certified |
| P3.3 | Manager and worker envelopes | Archetype allowlist, grant checks, no self-escalation/cross-venture tests | Envelope certified |
| P3.4 | Teardown and recovery | Revocation, quarantine, reconstruction from durable state, crash/retry tests | Recovery certified |
| P3.5 | P3 certification | Separate denominator, raw evidence, technical/non-technical report, human review | P3 exit recorded |

## 3. P3.0 deliverables

- phase3-policy-spec-v1.0.md
- phase3-implementation-plan-v1.0.md
- schemas/p3/*.schema.json
- tests/p3/fixtures/p3-0-contract-fixtures.json
- tests/p3/test_p3_contracts.py
- docs/adr/ADR-P3-001-contract-boundary.md
- docs/reviews/P3-000-contract-review.md

No database migration is introduced by P3.0. Durable venture and sandbox state is deferred to P3.1–P3.4 after the contract review.

## 4. Evidence and review

P3.0 evidence must record the exact source commit, schema hashes, fixture hash, test command, raw output, negative-test results, and limitations. The review must distinguish contract validation from actual sandbox isolation, recovery, and production readiness.

The P3.0 denominator is local to P3.0 and must not be added to the P2 denominator or ADV-001–ADV-049.

## 5. Current boundary

P3.0 is authorized by docs/reviews/P2-006-acceptance.md, but this plan and its contracts remain subject to the P3.0 analyst/auditor review. Until that review is accepted, P3 remains planning/contract work only.
