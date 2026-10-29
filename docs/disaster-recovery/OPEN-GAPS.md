# Recovery gaps and acceptance register — 2026-10-29

**Verdict: DOCUMENTATION BASELINE PRODUCED; WHOLE-SYSTEM DR NOT CERTIFIED.** The following gaps cannot honestly be closed with source inspection alone.

| ID | Priority | Gap / evidence required to close |
|---|---|---|
| DR-01 | Critical | Prove encrypted **off-host** backups cover current Control broker signed DB, all CEO/Manager/Worker inference DBs and artifacts, Owner review DB, discovery state, ledger/Postgres state, and config manifests. Record exact restore paths and backup owners. |
| DR-02 | Critical | Demonstrate clean-room recovery of both hosts from documented images + Git + encrypted backups; independently verify original Ed25519 signed workflow chain and fail-closed state. Existing P7.2 exercise is synthetic. |
| DR-03 | Critical | Owner-controlled external custody, recovery and revocation runbook for signing keys, OpenBao, CA certificates, SSH/service credentials; identify custodians without storing secrets in repository. |
| DR-04 | High | Validate reconciliation of external paid model intents and finance/payment events after partial loss; ensure no silent retry or duplicate charging. |
| DR-05 | High | Verify backup coverage, retention, integrity, independent access and tested restore for CTKFamily separately. Option B integration not yet live. |
| DR-06 | High | Complete exact deployed systemd/config/network/firewall/package/ACL snapshot and baseline it in a **secret-redacted** machine-readable manifest. Pre-existing dirty worktree must be reconciled against production without destructive reset. |
| DR-07 | High | Define Owner-approved measurable RPO/RTO per database/service and test actual restore timing. Synthetic P7 targets are not observed production recoveries. |
| DR-08 | High | End-to-end restore with timer renewal after replacement certificates, revoked old identities and scheduled failure alerting; historic Nov 12 expiry is near-term operational risk. |
| DR-09 | Medium | Automate safe read-only documentation drift report and add document owner/review dates. Do not give an AI process authority to silently rewrite authoritative recovery procedures. |
| DR-10 | Medium | Verify new proposals arrive in Owner inbox after future CEO discovery cycles; current snapshot is initial cycle only. CEO autonomous feedback consumption not yet implemented, so no implied operational loop. |

## Audit acceptance checklist

An independent auditor should identify the actual backup IDs and UTC dates, verify manifests and integrity, inspect redacted configs against services, observe a clean-room restoration without network/business authority, run signed-chain and replay/deny tests, and report `ACCEPTED`, `CONDITIONAL`, or `REJECTED` with precise scope. Acceptance of **documentation completeness** must not be confused with acceptance of **operational disaster recovery**.

## Existing evidence index

- Technical backup design (synthetic): `docs/reports/P7.2-BACKUP-RESTORE-IMPLEMENTATION.md`
- Topology: `docs/reports/P7.1-TOPOLOGY-DEPLOYMENT-IMPLEMENTATION.md`
- Secrets/provider historical work: `docs/reports/P7.4-CREDENTIAL-PROVIDER-IMPLEMENTATION.md`
- Level2D signed hierarchy: `docs/operational-readiness/evidence/level2d-real-autonomous-hierarchy-20261029.md`
- Real cert renewal: `docs/operational-readiness/evidence/level2d-mtls-renewal-20261029.md`; `docs/operational-readiness/evidence/level2d-worker-renewal-live-20261029.md`
- Owner web review: `docs/operational-readiness/evidence/owner-idea-self-service-20261029.md`
- Initial discovery: `docs/operational-readiness/evidence/ceo-discovery-initial-20261029.md`
- Owner authority: `docs/owner-venture-approval-policy-v1.0.md`
