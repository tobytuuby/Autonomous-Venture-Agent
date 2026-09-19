# Autonomous Venture Agent — Phase 5 Policy Specification

## v1.0

**Status:** Proposed for review; not active  
**Phase:** P5 — Revenue, treasury, and financial operations  
**Predecessor:** P4 exit and acceptance  
**Execution class:** Synthetic integration first; gated test integration only

## 1. Objective and scope

P5 defines how synthetic revenue, treasury, reconciliation, and financial
operations are represented, validated, replayed, and governed without granting
graduated external authority. It extends the existing policy kernel and
financial governors; it does not replace them.

P5 does not authorize real revenue collection, real treasury movement, real
payments, broker execution, credentials, customer contact, deployment, or
capital allocation.

## 2. Requirements

- **FIN-501 — Synthetic revenue identity:** Every synthetic revenue event has an
  immutable event ID, source, amount, currency, venture scope, timestamp, and
  provenance.
- **FIN-502 — Ledger authority:** The authoritative financial state remains
  kernel-owned; a recording or model output cannot authorize a transfer.
- **FIN-503 — Deterministic reconciliation:** Replaying the same event set
  converges to the same synthetic ledger and reconciliation result.
- **FIN-504 — Idempotency and collision denial:** Duplicate delivery converges;
  changed content under an existing identity fails closed.
- **FIN-505 — Treasury simulation:** Synthetic balances, reserves, ceilings,
  allocations, and ratchets are bounded by existing financial governors.
- **FIN-506 — Human review:** Material financial decisions require an explicit
  human review record; no model, CEO, manager, worker, or ledger event can
  self-authorize.
- **FIN-507 — Provenance and taint:** Every derived balance and reconciliation
  result retains source hashes, policy version, configuration fingerprint,
  scope, and transformation lineage.
- **FIN-508 — Fail-closed authority:** Live payment, broker, credential,
  customer, deployment, capital, and external-action paths remain denied.
- **FIN-509 — Recovery:** Crash recovery, replay, quarantine, and rollback
  reconstruct synthetic state without widening authority.
- **FIN-510 — Separate evidence:** P5 test denominators and evidence archives
  remain separate from P0–P4 results.

## 3. Ordered increments

1. P5.0 — Synthetic revenue event and ledger boundary.
2. P5.1 — Deterministic reconciliation and duplicate/collision handling.
3. P5.2 — Treasury simulation, reserve/ceiling enforcement, and recovery.
4. P5.3 — Human review and capability-decision records.
5. P5.4 — Gated test-integration review; no graduated external action.

## 4. Authority invariants

P5 cannot weaken P0–P4 controls. Synthetic balances are not spendable funds.
A payment adapter, broker, credential, customer, deployment, or external
transport remains unreachable. Test integration, if later authorized, must
use isolated test identities, allowlists, bounded amounts, explicit time
limits, a kill switch, and independent review.

## 5. Exit gate

P5 may exit only after every increment has independent tests, negative tests,
replay and crash-recovery evidence, authority-denial evidence, a manifest,
technical and non-technical assessments, and explicit human acceptance.
P6 remains blocked until the P5 exit decision is recorded.

## 6. Forbidden shortcuts

Do not treat a synthetic receipt as revenue, a simulated balance as capital, a
reconciliation result as authorization, or a test-provider response as proof of
production readiness. Do not use live credentials, real funds, real customer
contact, or real payment/broker execution in P5.
