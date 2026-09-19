# Autonomous Venture Agent — Phase 6 Policy Specification

## v1.0

**Status:** Proposed for review; planning authorized; implementation not authorized
**Phase:** P6 — Portfolio operations and shared services
**Predecessor:** P5 synthetic-only scope closed at `2fe141486c4a5d4bcac133e3e040eb52b734738a`
**Execution class:** Synthetic-only; no test-provider or live integration

## 1. Objective and scope

P6 defines how multiple synthetic ventures are represented, coordinated, reported,
quarantined, harvested, and wound down as a portfolio while preserving
venture isolation, kernel ownership, financial governors, provenance, and
configuration-fingerprint continuity.

P6 may compose P2 opportunity/thesis outputs, P3 venture and sandbox contracts,
P4 operational records, and P5 synthetic financial records. It may not turn any
of those records into authority to contact customers, deploy software, move
capital, execute payments, use brokers or credentials, or perform network or
other external actions.

## 2. Policy requirements

- **PORT-601 — Portfolio identity:** Every portfolio, venture membership,
  relationship, and portfolio decision has a durable identity and scope.
- **PORT-602 — Isolation:** A portfolio view may aggregate explicitly permitted
  metadata, but a venture's private state, grants, task data, and outputs
  cannot be read or mutated by another venture.
- **PORT-603 — Kernel ownership:** Portfolio services are advisory or
  kernel-owned. CEO, Venture Manager, worker, shared service, ledger, and
  report outputs cannot self-grant capabilities.
- **PORT-604 — Bounded coordination:** CEO-to-manager coordination uses
  typed, attributable, replayable coordination packets with role, venture,
  capability, policy, and configuration checks.
- **PORT-605 — Shared-service demand:** A shared service is provisioned only
  from kernel-verified demand with an allowlisted service class, scope,
  quota, expiry, and evidence lineage.
- **PORT-606 — Stateless shared execution:** Shared services receive no
  ambient venture authority and cannot retain cross-venture secrets or
  unscoped mutable state.
- **PORT-607 — Aggregate anomaly controls:** Portfolio controls detect
  cross-venture leakage, slow drift, duplicate beneficiaries, structuring-like
  patterns, quota exhaustion, stale evidence, and configuration mismatch.
- **PORT-608 — Selective quarantine:** One venture or service can be frozen,
  quarantined, or wound down without silently disabling unrelated ventures.
- **PORT-609 — Harvest and reinvestment:** Harvest and reinvestment remain
  synthetic decision records only; P5 balances are informational and
  non-spendable.
- **PORT-610 — Provenance continuity:** Every derived portfolio result retains
  source identities and hashes, policy version, configuration fingerprint,
  scope, taint, transformation lineage, and decision timestamp.
- **PORT-611 — Recovery:** Restart, retry, duplicate delivery, partial
  completion, quarantine, and wind-down converge to an auditable state without
  authority widening.
- **PORT-612 — Fail-closed authority:** All nine live-authority fields remain
  denied at every P6 boundary. No P6 record can authorize P7 behavior.
- **PORT-613 — Evidence separation:** P6 evidence has its own denominators,
  manifests, raw outputs, technical assessment, non-technical assessment, and
  human decision. It cannot replace P0–P5 evidence.

## 3. Execution boundary

Permitted: static/unit tests, deterministic synthetic fixtures, isolated
synthetic ventures, shadow reasoning, effect-free portfolio reports, simulated
quarantine/wind-down, and non-spendable harvest/reinvestment records.

Not permitted: test-provider integration, real or test credentials, payment or
broker calls, customer contact, deployment, capital movement, network action,
venture launch outside approved synthetic fixtures, worker execution outside
existing synthetic contracts, or production scheduling.

## 4. Exit gate

P6 may close only after each increment has a separate denominator and evidence
manifest; isolation, coordination, shared-service, anomaly, quarantine,
harvest, recovery, provenance, fingerprint, and authority-negative tests pass;
raw evidence is preserved; limitations are recorded; full prior regression
remains green; and a human operator records ACCEPTED, BLOCKED, or PARTIAL.

P7 remains the first phase where real external action may be considered.
