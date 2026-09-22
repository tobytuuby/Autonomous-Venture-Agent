# P7.4 Entry Decision

## Decision

**Status:** AUTHORIZED FOR PLANNING AND IMPLEMENTATION  
**Phase:** P7.4 — Credential and provider-boundary readiness  
**Decision authority:** Kalaap Das, human approval authority and independent reviewer  
**Decision date:** 2026-09-22  
**Branch:** phase7/p7-4-credential-provider-boundary  
**Predecessor:** P7.3 accepted at bc925ce  
**Predecessor evidence:** 9/9 focused methods, 32/32 cases, 375/375 full regression

## Authorization

Kalaap Das explicitly authorized P7.4 planning and implementation. This entry decision records that authorization before P7.4 source implementation. The planning package is committed separately from implementation so an auditor can verify that planning authorization and implementation are distinct events.

## Scope

P7.4 covers only synthetic or isolated credential custody, rotation, revocation, provider allowlisting, dependency pinning, redaction, identity binding, and terminal fail-closed behavior. It includes focused positive, negative, injected-failure, and recovery tests plus a self-auditing GitHub evidence packet.

P7.5, P7.6, P8, live credential issuance, real provider access, external contact, production deployment, and any live action are out of scope.

## Required invariants

- Synthetic, shadow, or isolated pre-production only.
- All nine live authorities remain denied: network, broker, payment, credential, deployment, customer, capital, venture, and worker.
- No live credential, provider account, secret store, real CEO, external contact, customer action, capital/payment action, deployment, broker, network, venture, worker, or real-world action.
- Model output never authorizes execution or credential control.
- No filesystem, network, database, queue, provider, credential-store, deployment, or host mutation I/O.
- Every case result includes source/configuration hashes, environment identity, timestamp, command, reviewer identity, evidence hash, and external/unauthorized/live-credential flags.
- Implementer cannot be the sole reviewer.
- Every planning document, source change, test, evidence artifact, and decision is committed and pushed.

## Auditor-access requirement

The independent auditor does not have bridge access to run tests. The P7.4 packet MUST therefore support a read-only GitHub audit without test reruns. It must separately expose planning audit and implementation audit, including commit lineage, exact source/test hashes and inventories, 40 case envelopes, raw logs, manifest hashes, requirement-to-code mapping, and the recorded reviewer/acceptance decisions.

The packet must state that its test results are recorded execution evidence; it must not claim the auditor reran the tests.

## Entry gate result

The P7.4 planning and implementation gate is recorded as authorized. Implementation may proceed only after this entry decision is committed. This record does not accept P7.4 and does not authorize P7.5, P8, live credentials, provider access, or production deployment.
