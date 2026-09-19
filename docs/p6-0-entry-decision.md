# P6.0 Implementation Authorization

**Status:** IMPLEMENTATION AUTHORIZED — P6.0 ONLY
**Decision date:** 2026-09-19
**Baseline:** `2fe141486c4a5d4bcac133e3e040eb52b734738a`
**Planning commit:** `d05f71dfeff31e2da5c8e93e611c2dfad4106ab9`

## Decision

The human operator authorizes implementation of **P6.0 — Portfolio identity and
registry** under the Phase 6 synthetic-only plan.

## Authorized scope

- Synthetic portfolio identity and registry contracts.
- Synthetic venture membership and lifecycle records.
- Explicit venture scope and allowlisted aggregate views.
- Deterministic duplicate/collision denial and stale-version rejection.
- Read-only portfolio reporting fixtures.
- Focused P6.0 tests and evidence only.

## Conditions

Before implementation execution begins, the implementer must:

1. Confirm the clean bridge workspace and exact baseline.
2. Define and commit the P6.0 focused denominator and synthetic fixture set.
3. Define the canonical P6 configuration manifest and fingerprint inputs.
4. Verify all nine live-authority fields remain denied.
5. Preserve P0–P5 provenance, taint, recovery, and evidence boundaries.
6. Stop and return for review on any authority widening, external call,
   credential/provider use, cross-venture leakage, or fingerprint failure.

## Not authorized

This decision does not authorize P6.1–P6.5, shared-service execution,
coordination beyond P6.0 records, test-provider integration, payment, broker,
credentials, customer contact, deployment, network action, capital movement,
real venture or worker execution, or any live authority.

**Human operator:** Kalaap Das
**Decision:** AUTHORIZE P6.0 IMPLEMENTATION ONLY
**Signature:** Kalaap Das
**Date:** 2026-09-19
