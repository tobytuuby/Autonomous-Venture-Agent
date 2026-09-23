# P7.5 Worker Authority Boundary — Policy Specification

## Status and boundary

Version: 1.0 planning draft  
Phase: P7.5 — Worker Authority Boundary  
Predecessor: P7.4 accepted at b14978a4c23adec937b24341fe1d7169be352881  
Execution class: Synthetic, shadow, or isolated pre-production only  
Decision state: Planning-only; implementation not authorized

P7.5 verifies that worker-shaped identities, admission records, capability envelopes, task packets, revocation, replay handling, crash recovery, and cross-venture isolation remain kernel-owned and fail-closed. It does not create a runnable worker, attach a real CEO, spawn a venture, dispatch a task, or enable worker authority.

## Normative invariants

1. A worker may be represented only as a synthetic descriptor or recorded task envelope. No worker process, thread, container, subprocess, queue consumer, browser, shell, network, provider, credential store, database, deployment, customer, capital, payment, broker, venture, or external I/O may be invoked.
2. Worker identity MUST be separate from CEO, manager, venture, portfolio, task, capability, and execution identities. Every record MUST bind a unique worker ID, parent manager ID, venture ID, portfolio scope, policy version, configuration fingerprint, correlation ID, idempotency key, and provenance chain.
3. Admission MUST be explicit, synthetic-only, bounded to an approved worker archetype, bounded to one venture scope, and denied by default when identity, scope, policy, configuration, provenance, or authority data is missing, stale, replayed, or mismatched.
4. A worker capability envelope MUST be a non-widening subset of its originating envelope. Workers MUST NOT self-escalate, delegate, mint grants, approve their own admission, or convert model output into authority.
5. All nine live authorities—network, broker, payment, credential, deployment, customer, capital, venture, and worker—MUST remain false before and after every case. synthetic_only=true and effect=none are mandatory.
6. Provenance MUST be immutable and hash-linked from admission through task recording, denial, revocation, quarantine, and recovery. Missing, altered, incomplete, or cross-scope provenance MUST fail closed.
7. Revocation MUST be monotonic and authoritative. A revoked worker, grant, task, venture, or parent scope MUST remain unusable through retries, replay, recovery, or stale packets.
8. Request identity MUST be idempotent. Reusing an ID with changed content MUST be quarantined; replaying an identical denied or accepted record MUST not create a new authority or effect.
9. Crash, timeout, partial-write, retry, and restart recovery MUST default to denial or quarantine. No recovery path may restore a capability or task state that was not present in the authoritative synthetic record.
10. Cross-venture access MUST be denied even when portfolio membership, manager identity, capability names, or task content are otherwise valid. A worker may see only its declared venture scope and permitted synthetic evidence.
11. Model output, approval-like text, worker instructions, fixture metadata, task content, or manager output MUST remain advisory data and MUST NOT authorize admission, capability, execution, revocation override, or recovery.
12. Any injected failure in admission, identity, capability validation, provenance, revocation, replay, persistence, recovery, or isolation MUST produce a terminal fail-closed result with no external effect.

## Explicit exclusions

P7.5 does not authorize live worker execution, real CEO attachment, venture spawning, customer contact, capital or payment activity, broker or network activity, deployment, credentials, provider access, production rollout, or P7.6. Acceptance of P7.5 evidence would remain pre-production readiness evidence only.
