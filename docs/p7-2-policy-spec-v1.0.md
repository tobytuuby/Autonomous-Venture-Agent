# P7.2 Policy Specification

## Status

**Version:** 1.0  
**Phase:** P7.2 — Backup, restore, and disaster recovery  
**Execution class:** Synthetic, shadow, or isolated pre-production only  
**Entry decision:** docs/p7-2-entry-decision.md  
**Independent reviewer:** Kalaap Das

## Objective

Demonstrate that authoritative synthetic state can be backed up, integrity-checked, restored, and recovered after simulated service or host loss without widening authority or producing an external side effect.

## Normative controls

1. Backups MUST use canonical, deterministic state serialization and record a state hash, backup hash, source commit, configuration fingerprint, environment identity, timestamp, and reviewer identity.
2. Verification MUST reject tampered bytes, mismatched checksums, incomplete manifests, wrong environment identity, wrong configuration fingerprint, and any live-authority grant.
3. Normal restore MUST produce a target state whose hash equals the expected source state hash.
4. Injected restore failure MUST fail closed and leave the pre-restore target unchanged; partial output must be quarantined in the synthetic fixture.
5. Service-loss recovery MUST restore from a verified backup into an isolated replacement service.
6. Host-loss recovery MUST restore into an isolated recovery host/namespace and must not contact or mutate a real host.
7. Recovery objectives MUST record synthetic RPO and RTO targets and observed values.
8. Model output, approval-like text, or fixture metadata MUST never grant execution authority.
9. All nine live authorities MUST remain false in every fixture and every result envelope.
10. No test may use a network, provider, credential, deployment, broker, payment, venture, worker, customer, or capital action.

## Required focused coverage

- Normal backup, verification, restore, and hash reconciliation.
- Corruption and manifest-integrity rejection.
- Environment/configuration mismatch rejection.
- Individual denial of all nine live authorities and attempted-use denial.
- Service-loss recovery and host-loss recovery.
- Injected restore failure containment and subsequent clean recovery.
- Recovery-objective recording and evidence completeness.

## Evidence contract

Each case result MUST include case ID, family, source commit, configuration fingerprint, environment identity, command, UTC timestamp, expected and observed outcome, state/backup hashes when applicable, external_action=false, unauthorized_action=false, live_credential=false, reviewer identity, and result status. JSONL case envelopes and an execution manifest MUST be retained under tests/certification/p7/results/.

## Pass/fail and boundary

The increment passes only with zero failed required cases, zero unauthorized actions, all corrupt/incomplete/mismatched backups rejected, normal and injected-failure recovery demonstrated, and full regression green. Passing evidence remains pre-production readiness evidence; it is not live proof and does not authorize P7.3 or P8.
