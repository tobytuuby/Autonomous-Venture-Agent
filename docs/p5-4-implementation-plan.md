# P5.4 Implementation Plan — Synthetic Integration Gate

**Status:** Planning authorized; implementation blocked
**Prerequisite:** Accepted P5.3 at 4035f9dc25bdd88c80e6f3e37572fc91a63e1411
**Execution class:** Synthetic validation only
**Policy scope:** Phase 5 closure and integration validation

## Objective

Validate that P5.0 through P5.3 compose into one durable, deterministic,
synthetic-only execution path:

P5.0 revenue event → P5.1 reconciliation → P5.2 treasury simulation →
P5.3 human-review record.

P5.4 is an integration gate, not an authority-unlock mechanism.

## Planned artifacts

- `tests/p5/test_p5_4_integration.py`: composition and boundary tests.
- `tests/certification/p5-4-manifest.json`: focused and regression evidence.
- `tests/certification/p5-raw/P5-4.json`: raw synthetic evidence.
- `docs/p5-4-certification-report.md`: implementation evidence, not acceptance.
- A separately signed P5.4 implementation authorization before code changes.

## Required invariants

1. The complete P5 chain preserves one configuration fingerprint.
2. Revenue records, reconciliation receipts, treasury results, and review
   records retain provenance and deterministic hashes.
3. Replaying the complete chain converges without duplicate side effects.
4. Review records remain advisory and do not grant capability.
5. Treasury results remain non-spendable with `effect: "none"`.
6. Cross-venture and cross-configuration composition fails closed.
7. Any live-authority field at any stage denies the integrated operation.
8. SQLite reopen/recovery preserves the same synthetic records.
9. No test-provider, broker, payment, credential, deployment, customer,
   capital, venture, worker, or network execution path is invoked.

## Planned acceptance tests

- complete P5.0→P5.3 happy-path composition;
- replay convergence across the complete chain;
- provenance and taint continuity;
- configuration-fingerprint continuity;
- cross-venture denial;
- cross-configuration denial;
- live-authority denial at each stage;
- non-spendable treasury result enforcement;
- capability-free human-review enforcement;
- durable recovery after reopening each SQLite boundary.

## Acceptance gate

P5.4 implementation may begin only after a separate signed human
authorization is committed. Completion requires focused tests, full
regression, schema/manifest validation where applicable, raw evidence, clean
diff checks, and a separate formal acceptance decision.

P5.5 or any live integration remains out of scope and blocked.
