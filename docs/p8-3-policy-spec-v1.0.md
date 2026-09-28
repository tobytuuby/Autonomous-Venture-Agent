# P8.3 Synthetic Recovery and Wind-Down — Policy Specification

**Version:** 1.0  
**Phase:** P8.3  
**Execution class:** Synthetic, shadow, or isolated pre-production only

## Scope

P8.3 records and evaluates supplied synthetic recovery requests against an approved P8.0 charter. It models freeze, revoke, quarantine, restore, rollback, and wind-down state decisions in memory. It does not perform recovery, restore, rollback, wind-down, monitoring, or any external action.

## Mandatory invariants

1. Every request binds to an approved P8.0 charter hash.
2. Venture and authority class must match the approved charter.
3. Execution remains synthetic-only and effect-free.
4. All nine live authorities remain explicitly false.
5. Model output, external-action indicators, unauthorized-action indicators, and live credentials remain false.
6. Freeze, revoke, quarantine, and wind-down can only produce bounded synthetic state records.
7. Restore and rollback are denied as authority-widening controls.
8. Terminal revoked and wound-down states cannot be reopened.
9. Duplicate recovery IDs replay the same result; changed material with the same ID fails closed.
10. Failure injection produces terminal fail-closed quarantine.
11. Automatic stop is terminal.
12. No process, queue, browser, filesystem, network, provider, credential, customer, capital, payment, broker, deployment, venture, worker, or external action is performed.

## Explicit exclusions

P8.3 does not attach a CEO, launch a worker, access credentials, poll a provider, contact a customer, move capital, execute payment or broker actions, deploy software, create a venture, or authorize P8.4, P9, or P10.
