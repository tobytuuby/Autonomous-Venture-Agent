# P8.4 Synthetic Pilot Certification — Policy Specification

**Version:** 1.0
**Phase:** P8.4
**Execution class:** Synthetic, shadow, or isolated pre-production only

## Scope

P8.4 performs deterministic certification and closeout of the synthetic P8.0–P8.3 evidence package. It validates charter binding, expected phase denominators, evidence identity, independent human review metadata, and all-false authority indicators. It produces a synthetic certification record only.

## Mandatory invariants

1. Certification packets bind to an approved P8.0 charter.
2. Venture and authority class match the approved charter.
3. P8.0–P8.3 evidence has the expected passing denominators.
4. All nine live authorities remain false.
5. Live action, execution, external action, unauthorized action, live credentials, and model authorization remain false.
6. Certification requires independent human review metadata.
7. Any missing, mismatched, or drifted evidence produces BLOCKED.
8. Duplicate certification IDs replay idempotently; changed material fails closed.
9. Automatic stop is terminal.
10. P8.4 never authorizes P8.5, live operation, production rollout, or external action.

## Explicit exclusions

No CEO or worker attachment, credential access, provider polling, customer contact, capital movement, payments, broker actions, deployment, network, venture creation, live recovery, or external I/O is authorized or performed.
