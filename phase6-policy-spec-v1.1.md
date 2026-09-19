# Phase 6 Policy Specification v1.1 — P6.1 Addendum

Status: planning-only addendum. No implementation or authority change.

This addendum operationalizes PORT-604 bounded coordination while preserving PORT-601 through PORT-603 portfolio identity and isolation, PORT-610 provenance, PORT-612 fail-closed authority, and PORT-613 evidence separation.

## P6.1 policy decisions

- Coordination is a typed, kernel-owned decision record, not an authority grant.
- A packet must name one portfolio, one venture scope, sender, recipient, role, request, capability envelope, policy version, and locked configuration fingerprint.
- Routing must validate portfolio and venture membership against the accepted P6.0 registry.
- A recipient may not broaden the originating capability envelope or route outside the named venture scope.
- Self-escalation, cross-venture routing, missing provenance, stale or expired packets, fingerprint mismatch, replay collisions, and effectful actions are denied.
- Exact duplicate packets converge to the original decision; changed content under the same request identity is a collision and is denied.
- All nine live-authority fields remain false/denied. Coordination cannot grant them.
- Evidence for P6.1 is separate from P6.0 and must include raw outputs, a denominator, manifest hashes, and two independent certifications.

## Decision gates

P6.1-A through P6.1-D are planning sub-gates. They do not authorize code. Implementation requires a separate human decision recorded after these sub-gates. P6.1 acceptance requires focused and full regression evidence, provenance and fingerprint verification, authority-negative results, rollback/recovery evidence, and human acceptance.

## Recovery rule

Any policy invariant failure fails closed, records a reason and evidence hash, quarantines the affected scope where necessary, and permits only deterministic, idempotent recovery. No recovery path may perform an external action or self-grant capability.
