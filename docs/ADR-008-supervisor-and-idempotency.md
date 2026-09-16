# ADR-008: Durable jobs and mechanical recovery

## Status

Accepted — P0.7.

## Decision

Jobs carry unique idempotency keys through the entire execution path. Reclaiming a stale
claim does not create a second external side effect. The Supervisor transitions only from
objective health signals and performs bounded, broker-mediated repair operations. A repair
operation must re-use the pre-incident grant unchanged or narrower; policy, prompt,
manifest, capability, cost, and network changes are outside recovery and are rejected.

The PostgreSQL adapter uses a dedicated local broker database role with no login, superuser,
database-creation, or role-creation privileges. The authoritative queue is the agent_jobs
table, where claims use row locks with SKIP LOCKED. The in-memory classes remain deterministic
mechanism tests; the adapter is the production persistence boundary.

## Consequences

Recovery can restart, restore, reprovision, or quarantine a generic instance without
creating a new authority path. Exhausted repair budgets and repeated quarantines escalate
to quarantine rather than retry indefinitely.
