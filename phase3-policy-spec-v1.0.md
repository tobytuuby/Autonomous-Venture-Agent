# Autonomous Venture Agent — Phase 3 Policy Specification

## v1.0

**Status:** Proposed for P3.0 baseline-and-contracts review  
**Phase:** P3 — Venture formation and sandboxing  
**Predecessor:** P2.6 accepted; P3.0 authorized under synthetic-only and sandbox-only conditions  
**Execution class:** Synthetic integration and shadow reasoning only

## 1. Objective and scope

P3 defines how an accepted P2 thesis may be represented as an isolated synthetic test venture with a bounded shadow Venture Manager and typed worker archetypes. P3 owns identity, namespace, sandbox, manager and worker envelopes, provisioning, teardown, recovery, wind-down, and cross-venture visibility boundaries.

P3 does not authorize a real venture, external provider, customer contact, capital allocation, payment, credential use, broker execution, deployment, or production CEO action. P3 contracts are records and policy inputs; they are not execution authority.

P3 inherits every P0, P1, and P2 authority, provenance, recovery, kill-switch, financial, taint, and evidence invariant. P3 evidence has a separate denominator and must not be relabeled as P0, P1, or P2 evidence.

## 2. Requirements

- **VNT-001 — Venture identity:** Each test venture has a collision-resistant, immutable identity linked to exactly one accepted thesis and portfolio scope.
- **VNT-002 — Namespace isolation:** Every venture has an explicit namespace and sandbox identity; cross-venture reads, writes, grants, and task references are denied by default.
- **VNT-003 — Synthetic boundary:** Provisioning, manager, and worker contracts declare synthetic-only state and deny external action, capital, payment, credential, broker, and deployment authority.
- **VNT-004 — Manager envelope:** A manager is bound to one venture, one role, and a closed set of worker archetypes. It cannot self-escalate or authorize outside its envelope.
- **VNT-005 — Worker archetypes:** Workers are typed by archetype and task class. An archetype cannot create another identity, widen its grant, or access another venture.
- **VNT-006 — Provisioning determinism:** Synthetic provisioning is idempotent, records configuration and image fingerprints, and can be replayed from durable records without hidden host state.
- **VNT-007 — Recovery and teardown:** Destroyed sandboxes reconstruct from authoritative state. Teardown revokes grants, quarantines outputs, and preserves audit history.
- **VNT-008 — Provenance preservation:** Venture and sandbox records retain source hashes, policy version, configuration fingerprint, timestamps, actor, scope, correlation, and idempotency identifiers.
- **VNT-009 — Human review:** P3 entry, material contract changes, P3.0 exit, and any proposed authority expansion require an explicit operator review.
- **VNT-010 — No authority by record:** A model response, accepted thesis, manager envelope, worker output, or provisioning record cannot authorize a venture launch, capital, payment, credential, broker, deployment, or external action.

## 3. P3.0 interface contracts

P3.0 defines JSON Schema Draft 2020-12 contracts for VentureIdentity, SandboxDescriptor, ManagerEnvelope, WorkerArchetype, and ProvisioningRequest. All contracts require the common P3 envelope. Contracts reject undeclared authority properties and constrain prohibited authority fields to false.

No P3.0 contract contains secrets, provider credentials, live endpoints, or a direct execution command.

## 4. Authority invariants

The CEO remains shadow-only. P3 cannot spawn a real Venture Manager or worker, launch a real venture, make a customer-facing commitment, allocate capital, execute payments, call a broker, access credentials, deploy software, or perform an external action. A sandbox is an isolation and evidence boundary, not an authorization boundary that can bypass the kernel or broker. P3 cannot weaken P0/P1/P2 gates, denominator rules, taint handling, or recovery requirements.

## 5. P3.0 entry gate

P3.0 entry is satisfied only by the recorded P2.6 acceptance, a clean baseline, preserved P0/P1/P2 hashes and evidence references, and an approved P3.0 requirements/contract review. The implementation remains synthetic-only while the review is open.

## 6. P3.0 exit gate

P3.0 may exit only when all five contracts validate against synthetic fixtures; missing-envelope, wrong-scope, authority-widening, and undeclared-property negative tests pass; two distinct synthetic venture identities and namespaces are represented; manager and worker contracts deny self-escalation and cross-venture access; provisioning remains idempotency- and fingerprint-bound; raw test output, source hashes, manifest, and review record are preserved; and an analyst/auditor or delegated human operator records ACCEPTED, BLOCKED, or PARTIAL status.

Passing schema tests alone does not establish sandbox isolation or recovery; those are later P3 increments.

## 7. Forbidden shortcuts

Do not treat a venture identity as a launched venture, a sandbox descriptor as a live container, a manager envelope as an execution grant, or a worker output as authority. Do not use real accounts, real ventures, real capital, external providers, credentials, customer contact, production deployment, or live network access.

## 8. Change control

Requirement or invariant changes require phase3-policy-spec-v1.1.md or later. Implementation corrections that preserve requirements belong in a new P3 implementation-plan version. This v1.0 remains proposed until the P3.0 review record accepts it.
