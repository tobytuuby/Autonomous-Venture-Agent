# P8.1 Controlled Action Gate — Policy Specification

**Version:** 1.0  
**Phase:** P8.1  
**Execution class:** Synthetic, shadow, or isolated pre-production only

## Scope

P8.1 implements a non-executing boundary for controlled-action requests. It validates a request against an approved P8.0 synthetic preflight record and records a synthetic denial. It never performs live action and is not production-ready.

## Mandatory invariants

1. The request names exactly one venture and one authority class.
2. The request references a stable P8.0 charter hash present in the approved synthetic charter registry.
3. The request venture and authority class match the registered P8.0 record.
4. Execution class remains synthetic-shadow-isolated-pre-production.
5. `synthetic_only=true` and `effect=none` are mandatory.
6. All nine live authorities are explicitly present and false in the request schema.
7. Live credentials and live mode remain denied.
8. Model output or model approval text cannot authorize a request.
9. Written live-action approval must not be treated as execution authority; the P8.1 boundary remains denied.
10. Every submitted request returns `status=DENIED`, `live_action_permitted=false`, and zero-action indicators.
11. Duplicate submission with the same request identity and material is idempotent.
12. Automatic stop is terminal and blocks further submissions.
13. The gate performs no network, broker, payment, credential, customer, capital, venture, worker, deployment, process, or filesystem action.

## Explicit exclusions

This implementation does not execute a worker, venture, customer, capital, payment, broker, deployment, network, credential, or external action. P8.1 does not authorize production, a real CEO, live credentials, P8.2, P8.3, P8.4, P9, or P10.
