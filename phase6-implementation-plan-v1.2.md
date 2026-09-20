# Phase 6 Implementation Plan v1.2 — P6.2 Shared-Service Demand

Status: adopted for P6.2 planning and implementation; synthetic-only.
Baseline: c8c1b253a36a54d6153f95eb16d6c972d2473ca0 (P6.1 implementation accepted).
Locked P6.0/P6.1 configuration fingerprint: 8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11.

## Objective

Represent bounded shared-service demand and execute it through a deterministic, stateless, effect-free synthetic runner. Every demand and output must remain attributable to one registered portfolio, one registered venture, one originating P6.1 coordination request, and one configuration fingerprint.

## Boundaries

P6.2 covers demand typing, service-class eligibility, per-demand quota enforcement, expiry, provenance, output attribution, deterministic stateless replay, and cross-venture isolation. It does not create shared mutable state, ambient authority, external calls, provider integration, credentials, payments, broker activity, customer contact, deployment, capital movement, real venture execution, or worker execution.

P6.0 registry contracts and P6.1 coordination contracts are immutable inputs. P6.2 may consume their identities and decisions but may not broaden their authority.

## Demand contract

A demand must include demand_id, portfolio_id, venture_id, coordination_request_id, requester actor, service class, requested units, scope, eligibility metadata, quota metadata, policy version, locked fingerprint, source IDs and hashes, lineage, taint, creation and expiry timestamps, synthetic_only=true, effect=none, and a canonical hash.

Eligibility is deterministic: the service class must be configured, requested units must be positive and within its maximum per-demand quota, the demand must be unexpired, and the venture must be a member of the named portfolio. Missing, stale, cross-scope, mismatched, effectful, or fingerprint-discontinuous demand fails closed.

## Stateless runner

The runner has no ambient authority, no provider adapter, no network path, and no mutable cross-venture counter or queue. It derives a synthetic output hash from the canonical demand and configuration. Re-running the same demand produces the same result; changing demand identity, venture, service class, quota, or configuration changes or denies the result. The output contains explicit portfolio, venture, demand, coordination, service class, units, source lineage, fingerprint, synthetic-only, and effect-free attribution.

## Proposed sub-gates

1. P6.2-A — Demand schema and provenance review.
2. P6.2-B — Eligibility and quota review.
3. P6.2-C — Stateless execution and output-attribution review.
4. P6.2-D — Evidence readiness and authority-negative review.
5. P6.2 acceptance — focused evidence, full regression, certifications, and explicit human acceptance before P6.3.

## Planned focused denominator

Sixteen scenarios are required: valid demand; required fields; registry scope; coordination identity; quota-under-limit; quota-exceeded denial; service-class eligibility denial; expiry denial; stale-time denial; fingerprint mismatch; missing provenance; all nine live-authority fields denied; effectful/non-synthetic denial; output attribution; deterministic stateless replay; and cross-venture isolation.

## Evidence

Separate P6.2 raw focused output, P6.0–P6.2 focused output, full regression output, git-state, configuration manifest, technical certification, and non-technical assessment are required. The manifest must preserve commands, denominators, exit codes, warnings, hashes, and exact commits.

## Rollback and recovery

P6.2 creates no mutable service state to roll back. A rejected demand is not executed and may be recorded only as read-only evidence. If a future journal is added, it must be append-only, scoped to the originating venture, and replayable without widening authority. Any invariant failure quarantines the demand and preserves its reason and evidence hash.

## No-go conditions and non-goals

Stop for any cross-venture state, unbounded quota, missing output attribution, ambient authority, provider or network call, mutable shared queue, credential access, live-authority field, fingerprint mismatch, nondeterministic replay, or unreconstructable evidence.

P6.2 does not demonstrate production shared services, external execution, autonomous worker operation, capital or payment activity, customer operations, or P6.3 anomaly controls.

## Human authorization

P6.2 planning and implementation authorization was provided on 2026-09-19. P6.2 acceptance remains a separate gate. P6.3 planning or implementation requires separate human authorization after P6.2 acceptance.
