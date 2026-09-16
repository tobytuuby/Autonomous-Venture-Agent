# ADR-011: Deny-by-default manifests and breaker classes

## Status

Accepted — P0.10.

## Decision

A platform action is permitted only when its manifest is current, explicitly permits the
action, and does not list it as prohibited. Expiration is immediate; there is no implicit
renewal or grace period. Guardrail breakers are assigned latching, cooldown, or progressive
reset classes in advance. Latching reset requires authenticated human-operator authority.

The audit sampler chooses from the population independently of venture-engine control and
retains each immutable sample selection.

## Consequences

Synthetic P0.10 tests prove the controls without connecting to external platforms. Real
channel integrations remain outside this increment.
