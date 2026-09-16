# ADR-005: OPA Fail-Closed Defaults

- Status: accepted
- Phase: P0.4
- Scope: venture-control policy evaluation

OPA is the policy decision point for structured policy-change requests. The caller must treat an unreachable, malformed, timed-out, or otherwise uncertain OPA response as deny. No caller may convert an OPA failure into an allow decision.

The policy recognizes only two change types: narrowing and widening. A transaction exception is not a policy primitive. Narrowing changes may take effect immediately. Widening changes require the fixed delay for their risk class, and material edits do not preserve the original clock; the caller must submit a new effective time satisfying the full delay.

OPA is bound to loopback on venture-control. venture-agents receives no network path to OPA. The broker, not an agent, will own the caller-side timeout and fail-closed behavior.
