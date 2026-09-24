# P8 Limited Pilot — Policy Specification

**Version:** 1.0  
**Phase:** P8 — Limited and reversible pilot  
**Current implemented scope:** P8.0 synthetic preflight  
**Execution class:** Synthetic, shadow, or isolated pre-production until separate live-action approval

## Scope

P8 is repository-defined as a limited pilot, not general production. P8.0 validates a pilot charter and stop controls without performing live action. P8.1 and later live behavior remain blocked until a separate written live-action approval is recorded.

## Mandatory pilot invariants

1. Exactly one venture is named.
2. Exactly one authority class is named.
3. One bounded operating window is explicit and ordered.
4. A numeric exposure ceiling is finite and greater than zero.
5. A numeric loss ceiling is finite, non-negative, and no greater than exposure.
6. Named human approvers are present.
7. Monitoring and reconciliation plans are non-empty.
8. Automatic stop conditions are explicit and non-empty.
9. Written live-action approval remains PENDING during synthetic preflight.
10. All nine live authorities remain false; live credentials remain denied.
11. Synthetic preflight records have synthetic_only=true and effect=none.
12. Model output and approval-like model text cannot authorize a pilot.
13. An automatic stop is terminal for the preflight gate.
14. A charter identity collision fails closed.
15. P8.0 cannot execute a live action or external I/O.

## Explicit exclusions

No real CEO, worker execution, credential use, customer contact, capital, payment, broker, deployment, network, venture spawning, provider access, production rollout, or P8.1 live action is authorized by the P8.0 implementation.
