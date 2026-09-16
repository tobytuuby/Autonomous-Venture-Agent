# Phase 0 Status

Updated: 2026-09-16

## Current decision

Phase 0 is **not certified for real-model attachment**.

The CEO Stage 0 runtime is intentionally fail-closed. It may not start until an independently generated pre-model certification record proves that the full ADV-001 through ADV-049 suite passed 49/49 using role-bound red-team/test identities with no reasoning model attached.

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
| Kernel mechanism tests | PASS | 62 repository unit tests pass |
| P0.14 lifecycle fixtures | PASS as fixtures | Role, venture, worker, repair, and shared-service mechanisms exercised |
| Genuine ADV-001..049 suite | INCOMPLETE | Harness derives 32 PASS and 17 PENDING; no gate emitted |
| Pre-model CEO gate | ENFORCED | Missing or invalid gate file causes runner exit before provider construction |
| Real CEO shadow runtime | NOT ATTACHED | No real provider configuration is active |
| Stage 0 exit re-certification | NOT READY | No real model fingerprint or CEO-specific 49/49 rerun |
| Stage 1 micro-capital | BLOCKED | Requires Stage 0 exit gate and is outside Phase 0 |

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

The repository contains exactly 60 ordinary unittest methods, and discovery executes 60/60 successfully. The pre-model harness adds two harness tests, bringing discovery to 62/62. It now executes 32 explicit ADV cases and leaves the other 17 pending; those cases are not counted as passes.

## Next implementation work

Implement the remaining 17 ADV scenarios against their actual kernel boundaries. Each scenario must produce its own evidence, remain model-free, and be independently verifiable before it can contribute to a pre-model 49/49 gate.
