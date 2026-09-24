# P7.6 Independent Certification — Policy Specification

**Version:** 1.0  
**Phase:** P7.6 — Independent certification of P7.5  
**Predecessor:** P7.5 Worker Authority Boundary  
**Execution class:** Synthetic, shadow, or isolated pre-production only  
**Decision state:** Implementation authorized; acceptance decision remains separate

## Scope

P7.6 independently certifies the committed P7.5 implementation and evidence packet. It is a read-only audit boundary, not a worker runtime, execution bridge, production rollout, or authority-enablement phase.

The P7.6 implementation may inspect repository files, Git metadata, hashes, schemas, logs, evidence envelopes, source syntax, and test inventories. It may execute local synthetic tests. It must not modify runtime state, contact external systems, use credentials, attach a CEO, create a worker process, dispatch work, or enable any live authority.

## Normative invariants

1. The audit must verify the exact repository commit and ancestry of the P7.5 evidence source.
2. The audit must verify the 81 authority and 12 recovery case IDs are present exactly once.
3. Every P7.5 envelope must pass, preserve all nine authority flags as false, and report zero external, unauthorized, and credential actions.
4. Evidence hashes, source inventories, test inventories, schema validity, and runtime-log counts must be independently recomputed.
5. Static source inspection must reject external-I/O, process-spawning, network, or credential imports/calls in the P7.5 worker boundary.
6. The audit harness itself must be read-only with respect to runtime behavior; its output is evidence, not execution authorization.
7. A PASS from the harness must remain PENDING_HUMAN_INDEPENDENT_DECISION until a separately auditable reviewer decision is recorded.
8. P7.6 must not widen the synthetic-only boundary or begin P8.

## Explicit exclusions

No live worker authority, real CEO, venture spawning, customer contact, capital, payment, broker, deployment, network, provider, credential, database, queue, or external action is authorized.
