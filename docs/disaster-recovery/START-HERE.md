# Autonomous Venture Agent: START HERE AFTER AN INCIDENT

**Status: RECOVERY GUIDE / NOT YET LIVE-RESTORE CERTIFIED.** Updated 2026-10-29. Do not assume backups contain the most recent transactions, certificates or inference state. If either VM is compromised, prioritize isolation and independent key rotation rather than blindly restoring secrets.

## First 15 minutes (human Owner)

1. **Freeze authority.** Disable external/customer/payment/venture activation; do not approve financing or trigger workflows. Preserve any unaffected VM, read-only evidence and logs. Never issue a replacement Owner approval from an AI agent.
2. Establish what failed: Control, Agents, webserver, storage, credentials, or network. Record UTC times, last confirmed trusted audit sequence, current Git commit, and last verified backups.
3. Preserve evidence before restarting: systemd journals, broker workflow database and WAL, durable inference queues, role-signed event histories, owner reviews, and certificate/renewal logs. Restrict access; do not put secrets in GitHub or chat.
4. Consult [SYSTEM-INVENTORY.md](SYSTEM-INVENTORY.md), [RECOVERY-RUNBOOK.md](RECOVERY-RUNBOOK.md), [BACKUP-COVERAGE.md](BACKUP-COVERAGE.md) and [OPEN-GAPS.md](OPEN-GAPS.md). These are complementary; a green test suite does not prove restoration.
5. Do NOT automatically replay PENDING/ambiguous paid model calls. Do NOT repeat financial operations without external reconciliation. Preserve old approval history and apply the latest independent trust decisions.

## Recovery sources and precedence

- Authoritative **source code and versioned design**: private GitHub `tobytuuby/Autonomous-Venture-Agent`, exact release commit and `AGENTS.md`.
- Authoritative **operational state**: most recent integrity-verified backups and durable state on surviving hosts; never infer state from code commits.
- Authoritative **human authority**: externally held Owner Ed25519 signing identity and signed receipts, independently verified against pinned keys; approvals may be stale/expired after recovery.
- Authoritative **live configuration/secrets**: separately protected system backups/secret store under Owner control. `/etc` secrets, OpenBao state, certificates and application credentials are not reconstructed from repository docs.
- Historical evidence: `docs/reports/P7.2-BACKUP-RESTORE-IMPLEMENTATION.md` (synthetic only), `docs/operational-readiness/evidence/level2d-real-autonomous-hierarchy-20261029.md` (real service-level test), `docs/operational-readiness/evidence/owner-idea-self-service-20261029.md`.

## Minimum safe restored state

A restored system begins in **PREPARATION_ONLY / no money, no customer contact, no production authority** regardless of its previous mode. Verify host identity, restored signing-key trust, role isolation, database hashes/event order, mTLS and renewal expiry, inference intent reconciliation, authorization-deny tests and Owner review records *before* resuming limited services. Real capital/payment services remain disabled until separate human authorization and reconciliation.

## Who does what

- **Human Owner:** independently authorizes restart scope, key replacement, real business activity and capital. Never delegated to CEO.
- **Recovery operator:** validates infrastructure and records, performs backups/restores and collects evidence; does not generate Owner authorization.
- **AI CEO:** after explicitly enabled, proposes and delegates research, cannot self-authorize venture admission or capital.
- **Claude independent auditor:** may review evidence and challenge claims; auditor verdict is not Owner authorization.

## Essential pointers

- [Recovery procedure](RECOVERY-RUNBOOK.md)
- [Runtime/system inventory](SYSTEM-INVENTORY.md)
- [Backup coverage and validation checklist](BACKUP-COVERAGE.md)
- [Known unverified gaps and acceptance conditions](OPEN-GAPS.md)
- `docs/owner-venture-approval-policy-v1.0.md`
- `docs/reports/P7.1-TOPOLOGY-DEPLOYMENT-IMPLEMENTATION.md`
- `docs/reports/P7.4-CREDENTIAL-PROVIDER-IMPLEMENTATION.md`
