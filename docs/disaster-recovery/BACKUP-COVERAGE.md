# Backup coverage and recovery evidence matrix

**Key distinction:** P7.2 (`docs/reports/P7.2-BACKUP-RESTORE-IMPLEMENTATION.md`) successfully exercised *isolated synthetic restore* and fail-closed validation; it is not proof of live whole-VM disaster recovery. Actual verified off-host backup coverage, storage retention and decryption/recovery access must be established separately.

| Material | Existing indication | What still needs proof |
|---|---|---|
| Git code, specs, tests | Private GitHub history and commit evidence | Independent clone at pinned commit, permissions and deployable dependencies |
| Postgres and ledger | `infrastructure/backup-postgres.sh`, `checkpoint-ledger.sh`; systemd backup/checkpoint timers observed | Last successful backup file, immutable/off-host copy, integrity, clean room restore, complete retention |
| Hierarchy broker SQLite | Durable live workflow, 11-transition acceptance chain | Consistent atomic snapshot with WAL; off-host coverage and signature/hash verification on restoration |
| CEO/Manager/Worker inference | Durable separate SQLite stores; restarts verified | Files and WAL captured, ambiguous paid-call reconciliation, no duplicate provider spending |
| Worker artifact payloads | Service/artifact evidence | Off-host copies, provenance and permissions, content integrity |
| Owner idea review | `reviews.sqlite`, discovery snapshots, feedback JSON | Inclusion in backups and independent restore; test proposal-digest revalidation |
| Service configs and systemd | Deployed Linux units | Signed manifest of unit files, environment FILE PATHS, service identities, ACLs, network routing and dependencies |
| OpenBao/cert trust | mTLS renewal timers and policy files | Secure off-host OpenBao snapshots/recovery shares and CA key recovery; future renewals and disaster-replacement certificates |
| Owner signing material | Out-of-band key policy | Owner-controlled encrypted key recovery and proof no agent can access it; rotation/revocation process |
| Finance/payment records | Governor code, finance drafts | External PayPal/bank reconciliation, API account recovery, ledger backup, transaction idempotency; no live payment connector claimed |
| CTKFamily | Separate webserver and repository | Separate verified web backups/login configuration; pending Option B route must not be assumed live |

## Verify before asserting DR READY

For **each** asset above record owner, path, backup tool, schedule, last completed UTC, verified hash, off-host storage destination, encryption/key custodian, retention, test restore date, RPO/RTO, and restoration dependency. If unknown, mark `UNKNOWN` rather than guessing.

## Non-destructive validation rules

Do not copy live SQLite files while writes are active without online backup API or a properly coordinated consistent snapshot; account for WAL. Keep recovery tests in isolated directories with outbound financial/business operations disabled. Compare database integrity and signed chain to pre-backup manifest, and journal any skipped data. Preserve original evidence before altering state.
