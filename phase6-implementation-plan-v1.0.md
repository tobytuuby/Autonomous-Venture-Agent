# Autonomous Venture Agent — Phase 6 Implementation Plan v1.0

**Status:** Planning authorized; implementation not authorized
**Baseline:** `2fe141486c4a5d4bcac133e3e040eb52b734738a` (`P5.4-ACCEPTED`)
**Execution class:** Synthetic-only
**Required workflow:** venture-control bridge, asynchronous commands with polling for long-running work

## 1. Objectives and boundaries

Build a deterministic, durable, and auditable portfolio layer over the accepted
P2–P5 contracts. P6 will demonstrate portfolio coordination and shared-service
governance using synthetic ventures and effect-free records. It will not enable
test providers or any live authority.

The master plan's P6 charter is refined here into implementation increments;
the master plan remains the project-wide phase registry.

## 2. P5 prerequisites

Before P6.0 implementation authorization:

1. Confirm P5 closure, tag, exact baseline, and clean bridge worktree.
2. Preserve P5's separate-ledger limitation as an explicit P6 test input; do
   not claim shared-database coexistence without a dedicated test.
3. Reuse P5 event, reconciliation, treasury-simulation, and human-review
   contracts without changing their authority semantics.
4. Define the P6 configuration manifest and canonical fingerprint inputs.
5. Record a human P6.0 implementation authorization separate from this plan.
6. Keep all nine live-authority fields denied and verify the denial before each
   increment.

## 3. Proposed increments and sub-gates

### P6.0 — Portfolio identity and registry

Create portfolio, membership, venture-scope, lifecycle, and portfolio-view
contracts. Prove deterministic membership updates, duplicate/collision denial,
scope filtering, stale-version rejection, and read-only aggregate views.

**Sub-gate P6.0-A:** schemas, identity invariants, focused tests, manifest,
raw evidence, diff check, and human acceptance.

### P6.1 — CEO-to-manager coordination

Create typed coordination packets linking portfolio, venture, actor role,
task/request identity, capability envelope, policy version, and configuration
fingerprint. Prove replay convergence, expiry, duplicate handling, and denial
of self-escalation or cross-venture routing.

**Sub-gate P6.1-A:** coordination and authority-negative evidence accepted.

### P6.2 — Shared-service demand and stateless execution

Represent demand, eligibility, quota, service class, expiry, and evidence
lineage. Use an effect-free synthetic service runner with no ambient authority,
no cross-venture mutable state, and explicit output attribution.

**Sub-gate P6.2-A:** demand provenance, quota, isolation, statelessness, and
configuration mismatch evidence accepted.

### P6.3 — Aggregate anomaly controls

Implement deterministic checks for cross-venture leakage, slow drift,
duplicate/structuring-like patterns, stale evidence, quota exhaustion,
configuration mismatch, and unexpected counterparty or beneficiary reuse in
synthetic data. Findings quarantine or require review; they do not execute.

**Sub-gate P6.3-A:** seeded anomaly fixtures, false-positive/negative review,
replay evidence, and human acceptance.

### P6.4 — Selective quarantine, harvest, reinvestment, and wind-down

Implement independent venture/service freeze, quarantine, recovery, harvest,
synthetic reinvestment proposal, and wind-down records. Verify grant
revocation and evidence preservation without affecting unrelated ventures.

**Sub-gate P6.4-A:** fault injection, recovery, selective isolation, and
wind-down evidence accepted.

### P6.5 — End-to-end portfolio certification

Compose P6.0–P6.4 across at least two synthetic ventures and one shared
service. Verify portfolio reporting, coordination, anomaly detection,
selective quarantine, recovery, and synthetic harvest/reinvestment while
preserving P2–P5 boundaries.

**Sub-gate P6.5-A:** focused P6 denominator, full regression, raw evidence,
technical/non-technical certification, limitations, and explicit human exit
decision.

## 4. Synthetic versus live capability matrix

| Capability | P6 decision |
|---|---|
| Synthetic portfolio records and reports | May be authorized by increment gate |
| Synthetic venture fixtures | May be authorized by increment gate |
| Shadow CEO/manager reasoning | May compose existing shadow contracts only |
| Synthetic shared-service runner | Effect-free and bounded only |
| Synthetic quarantine/wind-down | May be authorized by increment gate |
| Test-provider integration | DISABLED |
| Payment, broker, credential, customer, deployment, network | DISABLED |
| Real capital or financial movement | DISABLED |
| Production/live venture or worker execution | DISABLED |
| P7 authority or readiness claim | Not created by P6 |

## 5. Tests and evidence

Each increment requires focused unit, schema, integration, adversarial,
crash/recovery, replay/idempotency, provenance/fingerprint, and live-authority
negative tests as applicable. P6 evidence must include:

- exact source baseline, changed-file list, configuration manifest, and hashes;
- command, bridge identity, workspace, environment classification, denominator,
  warnings, failures, exit code, and raw output;
- per-scenario records, including unauthorized-action observations;
- technical and non-technical assessments kept distinct;
- a manifest that references raw evidence rather than replacing it;
- explicit P5 evidence references without relabeling P5 results as P6;
- limitations, nondeterminism, and independent-review status.

No test result or provider claim may be reported unless directly verified from
the underlying bridge execution evidence.

## 6. Provenance and configuration-fingerprint continuity

Every P6 input and derived record must carry:

- portfolio, venture, actor, role, and request identities;
- source record IDs and content hashes;
- policy/specification version;
- canonical configuration fingerprint;
- scope and taint classification;
- transformation/decision lineage;
- creation, expiry, and review timestamps.

A record with a missing, changed, stale, cross-venture, or cross-configuration
fingerprint fails closed. Replays must produce the same content hash and
decision outcome from the same canonical inputs. P6 must not normalize away
P5 provenance or promote synthetic/non-authoritative data to authority.

## 7. Rollback and recovery

All P6 state transitions must be append-only or recoverable through a
kernel-owned journal. On failure: stop the affected transition, preserve the
last known-good record, quarantine the affected venture/service, revoke
temporary synthetic grants, emit a reason and evidence hash, and allow
idempotent replay from the last accepted checkpoint. Recovery must be
selective; unrelated ventures remain readable and operational within their
synthetic boundary.

Rollback tests must cover process crash, duplicate delivery, partial
coordination, stale configuration, corrupted input, anomaly-triggered
quarantine, and wind-down/reopen. No rollback may restore a capability that
was not present in the accepted configuration.

## 8. No-go conditions

Stop and return to planning review on any authority widening, live/test
credential, provider endpoint, external network call, cross-venture data leak,
missing provenance, fingerprint discontinuity, nondeterministic replay,
unbounded aggregate exposure, failed quarantine, failed recovery, or evidence
that cannot be independently reconstructed.

## 9. Explicit non-goals

P6 does not implement or authorize production operation, test-provider
integration, payments, brokers, credentials, customers, deployment, capital
allocation, real revenue, live venture launch, autonomous worker execution,
P7 readiness, or removal of any P0–P5 control.

## 10. Human authorization requirements

This document authorizes planning only. Before P6.0 implementation, the human
operator must record a signed decision naming the increment, baseline,
execution class, test denominator, allowed synthetic fixtures, prohibited
capabilities, evidence requirements, and stop conditions.

Each subsequent increment requires its own acceptance before the next increment
is implemented. P6 exit requires a separate human decision. No model output,
agent output, test pass, or repository commit substitutes for that decision.
