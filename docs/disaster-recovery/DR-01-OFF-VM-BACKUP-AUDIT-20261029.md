# DR-01 — Real off-VM backup coverage audit

**Date:** 2026-10-29 UTC (read-only live inspection). **Verdict: PARTIAL COVERAGE VERIFIED; DR-01 OPEN / CRITICAL.** The CEO's bounded internal preparation operation was not altered. No finance, deployment, customer or Owner authority was activated.

## Direct observations

1. Control's `venture-control-postgres-backup.timer` schedules a daily 03:15 UTC `pg_dump --format=custom` through `infrastructure/backup-postgres.sh`; destination from systemd is `/var/backups/venture-control/venture-control`. Script defaults to database `postgres` and executes using the Postgres operating-system identity. Its systemd job last reported successful exit on 2026-10-29 03:25:53 UTC.
2. Control's `/var/backups/venture-control` is an NFS4 mount from TrueNAS `192.168.0.249:/mnt/Data/epsilon`, with systemd automount. This is **off-VM storage**, not independent/off-site storage or proof of immutable/encrypted retention. TrueNAS accessibility and underlying snapshot/replication protection are unverified.
3. The destination contains the dated archive `venture-control-postgres-20261029T032553Z.dump`, size **30,089 bytes**. `pg_restore -l` could list its archive catalog successfully. This proves it is structurally readable by pg_restore, **not** that the entire database has been restored, verified against production, or independently recovered.
4. Control's `venture-control-ledger-checkpoint.timer` uses `infrastructure/checkpoint-ledger.sh` with destination `/var/backups/venture-control/checkpoints`, on the same NFS mount. Dated checkpoint files exist through `ledger-head-20261029T220512Z.json` (329 bytes). The checkpoint is a state *head*, not a database backup.
5. Agents VM has persistent inference SQLite under `/var/lib/venture-manager/level2d/` and `/var/lib/venture-worker/level2d/`, including `run5/inference.sqlite` and active top-level inference stores. No venture-specific backup timer or NFS mount was observed in the inspected unit/mount inventory.
6. Control has persistent broker workflow/assignment/artifact/resource SQLite under `/usr/local/lib/venture-control-broker-level2c/artifacts/preparation-authority/`, CEO inference SQLite under `/usr/local/lib/venture-ceo-level2c/artifacts/`, discovery SQLite and the Owner review `reviews.sqlite`. No matching named SQLite files were found by the bounded search in the venture backup destination (maximum depth 3); that search cannot prove no backups exist elsewhere.
7. The archive's repeated 30,089-byte size across inspected dates and the default `BACKUP_DATABASE=postgres` mean we must confirm which real operational databases are covered. Archive listing is not evidence of completeness across all Postgres databases or separately held SQLite state.

## Coverage matrix at this audit

| Data class | Off-VM copy | Integrity evidence | Restore evidence | Conclusion |
|---|---|---|---|---|
| Control default PostgreSQL database | Dated `.dump` on TrueNAS | `pg_restore -l` succeeds | Not performed | **PARTIAL** |
| Control ledger head checkpoint | Dated JSON on TrueNAS | File exists; contents not independently chained here | Not performed | **PARTIAL; not backup** |
| Control broker workflow/artifacts and resources SQLite | Not found in inspected backup path | None | None | **UNVERIFIED** |
| CEO inference state/artifacts and discovery SQLite | Not found in inspected backup path | None | None | **UNVERIFIED** |
| Owner review decisions and snapshots | Not found in inspected backup path | None | None | **UNVERIFIED** |
| Agents Manager/Worker inference and artifacts | No corresponding job or NFS mount observed | None | None | **UNVERIFIED** |
| OpenBao, role signing keys, mTLS CA/certs, trust configurations | Recovery coverage not established | None | None | **UNVERIFIED; SECURITY CRITICAL** |
| Full machine configs/ACLs/systemd/OS images | No complete restoration manifest verified | None | None | **UNVERIFIED** |
| TrueNAS snapshots/off-site replication/encryption/retention | TrueNAS export exists | Not audited | Not audited | **UNVERIFIED** |

## Next necessary actions (no broad infrastructure change)

1. Enumerate *actual* Postgres databases and verify pg_dump archive contents against intended durable ledger tables, then restore a copy into an isolated, **non-operational** Postgres instance and compare integrity/row counts. Do not affect production database.
2. Build a signed/hashed, secret-free manifest of every live SQLite state store, artifact directory, systemd unit/config, and its designated backup destination on both VMs. Locate any existing backup mechanism first; only add missing paths.
3. For SQLite, use SQLite's online backup API or coordinated snapshots with WAL awareness, atomic staging, per-file hashes and explicit backup success checks. Never blindly copy an active SQLite database.
4. Validate the remote TrueNAS destination against independent access, protection, retention, encryption and restore capability. TrueNAS is on a separate host but might share the same physical-loss domain.
5. Confirm **out-of-band** recovery of private keys/OpenBao without disclosing any secrets to AI agents, logs or GitHub. Record Owner custodian and sealed recovery procedures; test in isolation.
6. Run isolated two-VM restoration with all business/financial permissions disabled, verify event signatures, exact Owner review state and no duplicate paid inference; then request independent Claude acceptance.

## Scope and caveats

This audit did not stop, restart, reconfigure or enable any autonomous service. No off-host copies of the missing classes were created. **DR-01 remains blocked**, and source-control documentation is not an alternative to recovered data and keys. Findings are specific to the inspected hosts/locations at the stated date; unknown means unknown, not definitely absent.
