# Phase 0 Status

Updated: 2026-09-17

## Current decision

Gate 1 pre-model certification is complete; Phase 0 is **not yet certified for real-model attachment**.

The CEO Stage 0 runtime is intentionally fail-closed. It may start only after an independently generated pre-model certification record proves that the full ADV-001 through ADV-049 suite passed 49/49 using role-bound red-team/test identities with no reasoning model attached. Gate 2 has a committed 49-entry shadow report and a configured provider fingerprint, but the external model-call claim is **not independently confirmed from repository evidence**; Stage 1 remains blocked.

## P0.15 stacked gates

### Gate 1: pre-model kernel certification

Required before any real model touches the system:

- ADV-001 through ADV-049 are executed as 49 distinguishable adversarial scenarios.
- Test identities are role-bound red-team identities representing the Portfolio CEO and Venture Manager roles.
- The reasoning model is not imported, attached, or used by the suite.
- The suite produces independently derived per-test verdicts.
- The final record contains 49 passes, zero pending cases, and zero unauthorized external actions.

The runtime validator is implemented in agents/ceo/gates.py and the default startup record is /etc/venture-ceo-kernel-gate.json. The repository example is deliberately NOT_CERTIFIED and is never a valid startup record.

### Gate 2: Stage 0 exit

After Gate 1, a real CEO may run only in shadow mode with the frozen broker-mediated tool vocabulary. Before Stage 1 is considered:

- The full 49-case suite is rerun against the exact real CEO configuration.
- The manifest contains the actual model_family and SHA-256 ceo_prompt_hash.
- ADV-040 is explicitly rerun against the real CEO configuration.
- The exit manifest proves 49/49 for that fingerprint.

Stage 1 real micro-capital is outside Phase 0 and remains unavailable.

## Evidence status

| Area | Status | Evidence |
|---|---|---|
| Kernel and integration tests | PASS | 73 repository unittest methods pass, including BOOT-001–BOOT-006, adapter coverage, manifest integrity, and the composed treasury/payment path |
| P0.14 lifecycle fixtures | PASS as fixtures | Role, venture, worker, repair, and shared-service mechanisms exercised |
| Genuine ADV-001..049 suite | PASS | Harness independently executes all 49: 49 PASS, 0 FAIL, 0 PENDING; no unauthorized actions; no reasoning model attached |
| Pre-model CEO gate | PASS / ENFORCED | Harness-generated record satisfies 49/49, zero pending, zero unauthorized actions, role-bound identities, and no reasoning model |
| Real CEO shadow runtime | PASS / SHADOW-ONLY | `gpt-5.6-sol`; four broker schemas; no execution |
| Stage 0 exit re-certification | CLAIMED / NOT INDEPENDENTLY CONFIRMED | Committed 49-entry report and configured `https://api.openai.com/v1` fingerprint; repository evidence cannot prove the external calls occurred |
| P0.16 treasury/payment path | PASS / SYNTHETIC RED-TEAM ONLY | BootstrapTreasury → RealPaymentAdapter composition passes idempotent retry, commit-after-adapter-success, ratchet preservation, and zero live external actions |
| Stage 1 micro-capital | BLOCKED | Real capital remains outside Phase 0 and unavailable |

## History audit

The 2026-09-16 certification-related history shows:

- P0.13 added a 24-of-49 manifest and generic unittest smoke harness.
- P0.14 added lifecycle fixtures and durable thesis/shared-service schemas.
- P0.15 added the restricted CEO runtime, provider wiring, service-account wiring, and path correction.
- No commit in the inspected history demonstrates a genuine role-bound ADV-001..049 run with per-test execution evidence.
- The former P0.14 49/49 claim was a self-authored manifest assertion and is not accepted as certification.

Relevant corrective commits:

- 94a8d1d — Enforce stacked CEO certification gates
- b0b2d1c — Close Phase 0 test evidence verification item
- e057951 — Build fail-closed role-bound pre-model harness
- c9d7928 — Expand pre-model adversarial coverage to twelve scenarios
- 41e2984 — Expand pre-model adversarial coverage to thirty-two scenarios
- e527437 — Execute every pre-model scenario and fail unsupported cases
- (current) — Add faithful integration, integrity, finance, and shared-service coverage

## Verification closure

The remaining test files were independently read on 2026-09-16:

- tests/test_compliance.py
- tests/test_compute.py
- tests/test_execution.py
- tests/test_finance.py
- tests/test_kill_switch.py
- tests/test_lifecycle.py
- tests/test_provenance.py
- tests/test_supervisor.py

The repository currently contains 73 discovered unittest methods. The complete run executes all 49 explicit ADV cases and independently derives 49 PASS, 0 FAIL, and 0 PENDING. Supplemental BOOT, adapter, manifest-integrity, and synthetic treasury/payment-path tests are separate from the ADV denominator. No case is silently skipped.

## Stage 0 readiness

Gate 1 is complete. The read-only readiness validator is `tests/certification/stage0_readiness.py`; it checks the installed pre-model gate, the frozen four-schema CEO tool list, the prompt hash, and whether provider environment variables are present. It does not call a model, enable external actions, or start the CEO service.

The current machine has a provider configuration in the approved secret boundary, but that configuration is not itself repository-verifiable evidence that the Gate 2 calls occurred. The endpoint is `https://api.openai.com/v1`, the configured model name is `gpt-5.6-sol`, and the token is not committed. Real values must never be committed.

The service must remain shadow-only and disabled until the readiness record is reviewed. The committed raw report and manifest record the configured fingerprint and 49 scenario results, but the Gate 2 status remains claimed/not independently confirmed because the certifier does not preserve independently verifiable HTTP evidence.

Stage 1 real micro-capital remains outside Phase 0 and unavailable.

## Next implementation work

Keep the real CEO shadow-only and do not treat Gate 2 as independently confirmed without verifiable external-call evidence. Do not add browser, shell, file, generic execution, or direct integration tools. The P0.16 treasury-to-payment composition is wired only through the synthetic red-team certification path; do not enable a live provider, real external actions, or Stage 1 micro-capital. Real capital remains outside Phase 0.
