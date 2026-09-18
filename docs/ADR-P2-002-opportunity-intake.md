# ADR-P2-002: Typed idempotent opportunity intake

- **Status:** Accepted for P2.1 implementation
- **Date:** 2026-09-18
- **Scope:** P2.1 opportunity intake

## Context

P2.1 must accept opportunities with typed provenance while preventing duplicate
processing, stale or tampered evidence, and cross-portfolio leakage. P2 remains
shadow-only and cannot turn an intake record into execution authority.

## Decision

Use a kernel-owned intake service with a durable opportunity record keyed by
`opportunity_id` and a unique `idempotency_key`. Store canonical JSON and
content hashes for the opportunity and each evidence envelope. Require exact
source-evidence references, verify each evidence payload against its declared
`source_hash`, enforce a configurable freshness window, and require every
evidence envelope to match the opportunity portfolio, policy version, and
configuration fingerprint.

Exact duplicate delivery converges to the existing record and appends a
`duplicate_delivery` event. Reuse of an idempotency key with changed content
or reuse of an opportunity identity with changed content is rejected. Intake
events use a hash chain for tamper evidence.

The synthetic integration uses SQLite for deterministic tests. The authoritative
PostgreSQL shape is recorded in
`migrations/p2/001_opportunity_intake.sql`.

## Consequences

P2.1 can prove idempotency, provenance preservation, freshness enforcement, and
scope isolation before later lifecycle behavior exists. The service rejects
invalid or unauthorized records before persistence and exposes no network,
broker, payment, credential, venture, or worker capability.

## Rollback and quarantine

A rejected intake creates no opportunity record. Existing records are never
deleted by the intake service. Later quarantine behavior belongs to P2.2/P2.4
and must preserve the append-only intake evidence and event history.
