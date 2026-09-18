# ADR-P2-001: Versioned P2 contract boundary

- **Status:** Accepted for P2.0 implementation
- **Date:** 2026-09-18
- **Scope:** Opportunity and thesis system contracts

## Context

P2 needs machine-checkable contracts before intake, normalization, thesis
identity, scoring, lifecycle, or replay behavior is implemented. The contracts
must preserve provenance and authority boundaries inherited from P0 and P1.

## Decision

P2 contracts are JSON Schema Draft 2020-12 documents under `schemas/p2/`.
Each contract carries policy version, configuration fingerprint, timestamps,
actor, portfolio scope, correlation, and idempotency identifiers. Evidence
records retain type, taint, source hash, and transformation history. Review and
replay contracts explicitly set external, capital, and launch authority to
false. All contracts reject undeclared properties.

P2.0 creates no durable SQL migration. Persistence changes belong to the
increments that introduce the corresponding behavior.

## Consequences

The contracts can be validated independently and replayed against a fixed
configuration. They are intentionally stricter than the existing legacy
schemas. Later increments may add versioned contracts, but may not weaken these
authority or provenance invariants without a new policy decision.

## Authority impact

These contracts cannot instantiate ventures or workers, allocate capital,
execute payments, call the broker, request credentials, contact counterparties,
or perform any external action. Acceptance is an analysis result only.
