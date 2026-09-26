# P8.2 Synthetic Monitoring — Policy Specification

**Version:** 1.0
**Phase:** P8.2
**Execution class:** Synthetic, shadow, or isolated pre-production only

## Scope

P8.2 observes supplied synthetic P8.1 records and performs deterministic reconciliation against the approved P8.0 charter registry. It detects boundary drift and records observations or quarantined findings. It never polls, connects to, or writes to an external system.

## Mandatory invariants

1. Every observation references an approved P8.0 charter hash.
2. Venture and authority class must match the approved charter.
3. Observations remain synthetic-only and effect-free.
4. All nine live authorities must be present and false.
5. Live action, external action, unauthorized action, and live credential indicators must remain false.
6. Model output cannot authorize an observation.
7. Exposure and loss values must be finite, non-negative, and compared against bounded charter ceilings.
8. Any authority, credential, action, model, scope, or ceiling drift produces a `QUARANTINED` finding and `stop_required=true`.
9. Duplicate event replay is idempotent; changed material with the same event ID fails closed.
10. Automatic stop is terminal.
11. The monitor performs no network, provider, credential, process, filesystem, customer, capital, payment, broker, deployment, venture, worker, or external action.

## Explicit exclusions

P8.2 does not execute live monitoring, attach a CEO, access telemetry providers, contact customers, move capital, launch workers, or authorize P8.3, P8.4, P9, or P10.
