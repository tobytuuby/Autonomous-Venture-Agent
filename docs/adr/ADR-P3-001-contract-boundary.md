# ADR-P3-001 — P3 Contract Boundary

**Status:** Proposed for P3.0 review  
**Date:** 2026-09-19

## Decision

P3.0 uses JSON Schema Draft 2020-12 contracts under schemas/p3/ for the synthetic venture identity, sandbox descriptor, shadow manager envelope, worker archetype, and synthetic provisioning request.

The contracts are deliberately declarative. They describe bounded records and requested synthetic state; they do not create identities, provision containers, grant capabilities, or authorize execution.

## Boundary

Every contract is bound to one portfolio scope and one P3.0 policy version; carries correlation, idempotency, actor, timestamp, and configuration fingerprint fields; requires synthetic-only state; denies cross-venture access, self-escalation, credentials, payment, deployment, and external action as applicable; and rejects undeclared properties.

P3.0 introduces no migration and no live provider or network integration. Provisioning, durable state, reconstruction, and revocation are deferred to later P3 increments.

## Consequences

The contract tests can demonstrate schema-level denial and fixture validity, but cannot by themselves prove runtime isolation, crash recovery, or production readiness. Those claims remain explicitly out of scope.
