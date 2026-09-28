# P9 Synthetic Boundary Hardening — Policy Specification

**Version:** 1.0
**Authority:** Kalaap Das, authorization recorded 2026-09-28
**Execution class:** Synthetic, shadow, or isolated only
**Status:** Implementation authorized within this specification

## Purpose and scope

P9 verifies that the accepted P8 safety boundary remains enforced under deterministic synthetic observations, scope-change proposals, replay, recovery simulation, and injected failures. The implementation produces in-memory synthetic records only. It does not grant operational authority, connect to providers, or establish production readiness.

P9 increments:
- P9.0: freeze the accepted P8 baseline and test denominator.
- P9.1: evaluate synthetic observations and fixture-only scope changes.
- P9.2: exercise deterministic replay, isolation, and injected-failure handling.
- P9.3: simulate bounded recovery state decisions and verify audit records.
- P9.4: independently review the evidence packet and certify synthetic scope only.

The implementation is one in-memory module. It accepts supplied records and a supplied in-memory charter map; it does not load charters, evidence, credentials, or configuration from external sources.

## Mandatory invariants

1. Execution class is exactly synthetic-shadow-isolated-pre-production; synthetic_only is true and effect is none.
2. All nine live authority fields are required and false on every accepted input and output.
3. No real CEO is attached. No live worker or venture authority is enabled.
4. Customer, capital, payment, broker, deployment, network, credential, provider, worker, venture, and external actions are never performed. No process, queue, browser, service, or filesystem is invoked by the runtime module.
5. Model output and approval-like text are untrusted informational fields. They cannot authorize, approve, or change disposition. A model authorization flag must be false.
6. Every record binds to a known charter hash, venture ID, and portfolio ID. Unknown, stale, or mismatched scope is rejected.
7. Scope variation is simulation-only and changes exactly one allowed fixture dimension: numeric limit, operating-window value, fixture venture count, or concurrency. Authority class and provider/dependency are prohibited dimensions.
8. Identical event ID and material replay the identical result. Reuse of an event ID with changed material fails closed and stops the boundary.
9. Per-scope sequences are strictly increasing. Cross-venture and cross-portfolio records and replay identities remain isolated.
10. Recovery controls only create synthetic state results: freeze, revoke, quarantine, or wind-down. Restore and rollback are denied. Revoked and wound-down are terminal.
11. Injected failures and authority/action drift fail closed. Stop is terminal. No retry bypasses a stop.
12. All canonical hashes are deterministic SHA-256 over canonical JSON. Non-finite numbers, malformed records, missing evidence identity, and hash mismatches are rejected or quarantined.
13. P9 output cannot authorize P10, production, or live operation.

## Explicit non-goals

No live expansion of venture count, authority class, exposure, operating window, provider/dependency, or concurrency; no live monitoring/recovery; no production-readiness claim; no model authority; no credential or provider adapter; no network, subprocess, filesystem persistence, deployment, worker/venture launch, customer contact, capital movement, payment, broker action, or P10 work.

The older roadmap draft's live expansion language is superseded for this authorized P9 scope by these constraints. It does not grant P10 or live authority.

## Pass rule

Every focused and regression test passes at declared denominators; all nine authority fields remain false; model authorization remains false; zero execution, external action, unauthorized action, credential, provider, and network activity; replay, isolation, recovery, and evidence integrity checks pass; and the evidence packet is accepted by an independent reviewer. Any unexplained discrepancy blocks P9 certification.
