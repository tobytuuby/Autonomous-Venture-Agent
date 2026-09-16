# ADR-007: Provenance and taint are causal state

## Status

Accepted — P0.6.

## Decision

Every derived record retains its parent lineage and the union of its source evidence IDs.
Taint is monotonic through normal derivation: summaries, paraphrases, and aggregations do
not lower it, and elapsed turns have no effect. Declassification is a separate operation
that requires authenticated human-operator authority and records an explicit approval ID.

P0.6 proves the mechanism with synthetic evidence. The production identity/authentication
binding is completed with the operator-authentication work in P0.11. Agent identities are
never accepted as declassifiers, regardless of headers or self-asserted claims.

## Consequences

The capability request already carries the provenance envelope reserved in P0.5. Broker
plan matching can consume this lineage now, while the full taint-aware decision refinement
is completed at the P0.6 integration boundary.
