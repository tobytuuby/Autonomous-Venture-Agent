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
| Kernel mechanism tests | PASS | 60 repository unit tests pass |
| P0.14 lifecycle fixtures | PASS as fixtures | Role, venture, worker, repair, and shared-service mechanisms exercised |
| Genuine ADV-001..049 suite | NOT CERTIFIED | No independently derived 49-case execution record found |
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

Relevant corrective commit:

- 94a8d1d — Enforce stacked CEO certification gates

## Next implementation work

Build the genuine role-bound red-team harness and its per-ADV-ID evidence output. The harness must be able to generate the pre-model gate record only from its own successful execution; hand-editing a JSON record, copying fixture counts, or relying on generic unittest discovery is not sufficient.
