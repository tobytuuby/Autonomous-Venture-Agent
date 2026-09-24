# P8.1 Controlled Action Gate — Policy Specification

**Version:** 1.0  
**Phase:** P8.1  
**Execution class:** Synthetic, shadow, or isolated pre-production only

## Scope

P8.1 implements a non-executing boundary for controlled-action requests. It validates a request against a completed P8.0 charter identity and records a synthetic denial. It never performs live action.

## Mandatory invariants

1. The request names exactly one venture and one authority class.
2. The request references a stable P8.0 charter hash.
3. Execution class remains synthetic-shadow-isolated-pre-production.
4. `synthetic_only=true` and `effect=none` are mandatory.
5. All nine live authorities remain false.
6. Live credentials and live mode remain denied.
7. Model output or model approval text cannot authorize a request.
8. Written live-action approval must not be treated as execution authority; the P8.1 boundary remains denied.
9. Every submitted request returns `status=DENIED`, `live_action_permitted=false`, and zero-action indicators.
10. Duplicate submission with the same request identity and material is idempotent; changed material with the same request ID fails closed.
11. Automatic stop is terminal and blocks further submissions.
12. The gate performs no network, broker, payment, credential, customer, capital, venture, worker, deployment, process, or filesystem action.

## Explicit exclusions

This implementation does not execute a worker, venture, customer, capital, payment, broker, deployment, network, credential, or external action. P8.1 does not authorize production, a real CEO, live credentials, P8.2, P8.3, P8.4, P9, or P10.
