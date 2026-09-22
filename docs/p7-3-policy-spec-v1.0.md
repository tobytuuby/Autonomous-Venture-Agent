# P7.3 Policy Specification

## Status

**Version:** 1.0  
**Phase:** P7.3 — Observability and incident response  
**Execution class:** Synthetic, shadow, or isolated pre-production only  
**Entry decision:** docs/p7-3-entry-decision.md  
**Independent reviewer:** Kalaap Das

## Objective

Demonstrate that synthetic operational events are auditable, metrics are deterministic, alerts are triggered and acknowledged, incidents are classified and escalated, retention rules are enforced, and evidence is preserved within the rehearsal window without external effects.

## Normative controls

1. Every audit event MUST have a stable event ID, event type, timestamp, environment identity, source/configuration fingerprint, severity, authority fingerprint, provenance hash, and synthetic-only flags.
2. Event integrity MUST be verifiable through canonical serialization and SHA-256. Tampered, incomplete, duplicate, or out-of-order event records MUST be rejected or quarantined.
3. Metrics MUST be deterministic and derived only from synthetic events. Threshold configuration MUST be bound to a configuration fingerprint.
4. Required alerts MUST trigger from deterministic thresholds and MUST require explicit synthetic acknowledgement. Missing, duplicate, or unauthorized acknowledgement MUST fail closed.
5. Incidents MUST map deterministically to severity, owner, escalation path, status, and stop condition. Model output or text MUST NOT create an acknowledgement or escalation authority.
6. Retention MUST preserve the required evidence window and reject early deletion or unbounded retention configuration.
7. Evidence preservation MUST record detection time, preservation time, raw-output hash, source/configuration hashes, and elapsed minutes. The rehearsal pass threshold is 15 minutes or less.
8. Injected failures in alert acknowledgement, incident escalation, retention, or evidence preservation MUST produce a terminal fail-closed state with no external effect.
9. All nine live authorities MUST remain false in every fixture and result envelope.
10. No real network, provider, deployment, credential, customer, payment, capital, broker, venture, worker, database, queue, or external alerting system may be invoked.

## Required coverage

- Event schema, IDs, ordering, provenance, and integrity.
- Deterministic metrics and threshold binding.
- Alert trigger, acknowledgement, duplicate/missing acknowledgement, and acknowledgement failure.
- Incident severity, escalation, owner, stop condition, and escalation failure.
- Retention boundary, early-delete rejection, and retention failure.
- Evidence preservation timing, hash completeness, 15-minute boundary, and preservation failure.
- Model-output non-authorization and all nine authority denials.
- Normal and injected-failure recovery for alerting, escalation, retention, and preservation.

## Evidence contract

Each case envelope MUST include case ID, family, source commit, source-file hashes, test file hash, configuration fingerprint, environment identity, runner/version, command, start/end timestamps, expected and observed disposition, result, assertion summary, raw output path/hash, capability and authority fingerprints before/after, provenance/ledger hashes where applicable, injected-failure details, evidence-preserved timestamp, external_action=false, unauthorized_action=false, live_credential=false, reviewer identity, and packet status.

The packet MUST separately identify planning artifacts, implementation artifacts, execution logs, generated case evidence, manifest, technical report, non-technical assessment, independent review, and human decision. No packet may rely on the auditor rerunning tests.

## Pass/fail and boundary

P7.3 passes only with zero failed required cases, zero unauthorized actions, all required alerts acknowledged, every incident class mapped to a runbook, preservation within 15 minutes, complete packet hashes, independent review, and full regression. Passing evidence remains pre-production readiness evidence and does not authorize P7.4, P8, live action, or production deployment.
