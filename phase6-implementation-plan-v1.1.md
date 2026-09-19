# Phase 6 Implementation Plan v1.1 — P6.1 Coordination

Status: adopted for P6.1 implementation; implementation remains synthetic-only.
Baseline: 9a493fa4054a39f1c669598b83435574fca0ece1 (P6.0 accepted).
Locked P6.0 configuration fingerprint: 8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11.

## Objective

Define a synthetic-only, kernel-owned CEO-to-manager coordination contract that routes requests only within explicitly authorized portfolio and venture scopes. P6.1 must preserve P6.0 identity, lifecycle, provenance, configuration, and fail-closed authority boundaries.

## Boundaries

Planning covers packet schemas, canonicalization, routing predicates, capability-envelope non-widening, replay/idempotency, expiry, rejection reasons, journal/recovery semantics, and evidence design. No implementation, provider integration, credentials, network calls, deployment, customer contact, capital movement, payments, broker action, real venture action, worker execution, or live authority is authorized.

The P6.0 registry and contracts are immutable inputs. P6.1 may reference them but may not re-authorize or broaden them.

## Proposed contract

Every coordination packet must contain portfolio identity, venture identity, sender and recipient actor identities, roles, request and correlation IDs, task identity, explicit scope, capability envelope, policy version, configuration fingerprint, source identities and hashes, lineage, taint, creation time, expiry, and canonical content hash.

Routing is accepted only when portfolio and venture scope match the kernel registry, actor roles are valid, the capability envelope is no broader than the originating request, the policy and locked fingerprint match, and the packet is unexpired. Missing, stale, cross-config, cross-venture, self-escalating, duplicate-with-different-content, or effectful packets fail closed.

## Proposed increments and sub-gates

1. P6.1-A — Contract and canonicalization design: schemas, field semantics, canonical hash, rejection taxonomy, and policy mapping reviewed.
2. P6.1-B — Scope and authority design: portfolio/venture routing, role constraints, non-widening capability envelopes, self-escalation and live-authority denials specified.
3. P6.1-C — Replay and recovery design: exact duplicate convergence, collision denial, expiry, journal ordering, quarantine, and idempotent recovery specified.
4. P6.1-D — Evidence readiness: test denominator, raw-output paths, manifest schema, technical certification, non-technical assessment, and human acceptance template complete.
5. P6.1 implementation gate: requires a separate explicit human authorization after P6.1-A through P6.1-D are accepted.

## Planned focused denominator

Eighteen synthetic-only scenarios are proposed: valid typed packet; required identity and scope fields; locked fingerprint continuity; fingerprint mismatch denial; missing provenance denial; exact duplicate convergence; changed-content collision denial; deterministic replay hash convergence; expiry denial; stale-time denial; cross-portfolio denial; cross-venture denial; self-escalation denial; capability-envelope widening denial; all nine live-authority fields denied; effectful/non-synthetic coordination denial; SQLite reopen durability; and schema/authority rejection.

The denominator is a plan, not a test result. No P6.1 tests are claimed or run by this planning change.

## Synthetic versus live capability

Synthetic capability is limited to deterministic in-process packet validation, routing decisions, journal state, replay, quarantine, and read-only evidence. Live capability remains denied for all nine P5 authority fields: live mode, external action, payment, broker execution, credential access, customer contact, capital allocation, deployment, and venture execution. No test provider or external integration is permitted.

## Required evidence

A future implementation must provide a separate P6.1 manifest, focused raw output, full-regression raw output, git-state output, configuration manifest, technical certification, and non-technical assessment. The manifest must identify the exact implementation commit, baseline, commands, denominator, hashes, and evidence paths. Raw output must remain immutable and distinct from summaries.

## Provenance and fingerprint continuity

P6.1 must carry forward the locked P6.0 fingerprint unchanged. Every packet, journal entry, routing decision, rejection, replay result, quarantine action, and evidence record must preserve scope, actor/role, source identity and hash, policy version, fingerprint, lineage, taint, and timestamps. Missing or mismatched provenance is a denial. Any proposed fingerprint change requires a new human-reviewed phase decision; it cannot be introduced by P6.1 implementation.

## Rollback and recovery

Coordination state must be append-only or journaled with deterministic ordering. On invariant failure, quarantine the affected packet or venture scope, revoke any temporary synthetic grant, preserve the rejection reason and evidence hash, and make recovery idempotent. Recovery must never replay an effectful action or widen authority. A rollback must be verifiable from raw journal and manifest artifacts.

## Explicit non-goals

P6.1 does not create autonomous management, shared services, capital or payment operations, production readiness, external communications, deployment, credential use, customer interaction, provider/test-provider integration, real venture execution, worker execution, or any live authority. P6.2 through P6.5 remain blocked.

## Human authorization

Planning acceptance does not authorize implementation. Before implementation, a human operator must accept this plan and authorize P6.1 implementation explicitly. Before P6.2, a separate human acceptance must review the complete P6.1 evidence package, technical certification, non-technical assessment, regression results, residual risks, and unchanged authority profile.
