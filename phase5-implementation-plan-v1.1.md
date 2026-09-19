# Phase 5 Implementation Plan v1.1

**Status:** P5.1 planning; implementation not authorized
**Supersedes:** P5.0 planning section in v1.0 for the active increment
**P5.0 baseline:** c25e743a509ffb6cbf8b00f23570ce734bbf55c8
**Execution class:** Synthetic integration only

## P5.1 — Deterministic reconciliation

### Objective

Derive a deterministic synthetic reconciliation result from a defined set of
P5.0 revenue events without creating authority to move funds or execute any
financial action.

### Required behavior

- Accept only P5.0 events with the same configuration fingerprint.
- Canonically sort source event identities before computation.
- Compute a cumulative synthetic balance in integer minor units.
- Preserve event IDs, event hashes, provenance, taint, scope, policy version,
  and configuration fingerprint.
- Produce a reconciliation receipt with a deterministic reconciliation hash.
- Replaying the same event set in any order converges to the same receipt.
- Changed or missing source content fails closed.
- Empty, cross-venture, cross-configuration, or authority-bearing inputs are
  rejected.
- A reconciliation result cannot authorize payment, broker, credential,
  customer, capital, deployment, or external action.

### Proposed interfaces

- kernel/p5/reconciliation.py
- schemas/p5/synthetic-reconciliation-result.schema.json
- tests/p5/test_p5_1_reconciliation.py
- tests/certification/p5-1-manifest.json
- tests/certification/p5-raw/P5-1.json

### Test denominator

The focused P5.1 suite must cover at least:

1. valid reconciliation;
2. order-independent convergence;
3. duplicate source identity handling;
4. changed-content collision denial;
5. missing-source denial;
6. cross-venture denial;
7. cross-configuration denial;
8. provenance and taint preservation;
9. authority-bearing result denial;
10. durable replay/crash recovery.

The full P0–P5.0 regression must remain green. Test results are not claims
until executed through the venture-control bridge and preserved in raw evidence.

### Evidence requirements

Each receipt must preserve the sorted source event IDs, source event hashes,
source provenance, cumulative amount, configuration fingerprint, policy
version, reconciliation hash, timestamp, and status. Raw test output must
record command, environment, denominator, warnings, failures, and exit code.

### Exit gate

P5.1 remains READY FOR REVIEW only after implementation, focused tests, full
regression, schema validation, diff check, evidence preservation, and a human
acceptance decision. P5.2 remains blocked until P5.1 is accepted.

### Prohibitions

No real funds, payment provider, broker, credentials, customer, deployment,
capital allocation, or external network action may be introduced.
