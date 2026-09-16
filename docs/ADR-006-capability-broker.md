# ADR-006: Capability broker enforcement boundary

## Status

Accepted — P0.5.

## Decision

All agent authority is represented by a broker-issued, narrow grant. The broker evaluates
the complete request context (agent, venture, plan, recent action graph, aggregate windows,
counterparty identity, novelty, behavioral baseline, and provenance envelope) before asking
OPA for the final capability-policy decision. OPA is a mandatory dependency: unavailable,
malformed, or denied policy input produces a deny, never an allow.

Grants are always time-boxed and may be single-use. A caller cannot delegate a wider scope
than the issuing policy permits, and the grant contains no credential material. The broker
keeps request/grant state in the authoritative database in production; the in-memory state
used by the P0.5 harness is an explicit deterministic test double until the broker persistence
migration is delivered.

P0.5 implements provenance field compatibility and action-graph checks. Taint propagation and
human-only declassification semantics are completed in P0.6.

## Consequences

The broker is the only issuance path. Fraud controls are composable and independently tested.
A broker or OPA outage stops new grants, which is the intended fail-closed behavior.
