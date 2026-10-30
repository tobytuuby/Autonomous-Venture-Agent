# DR-02 SQLite-aware TrueNAS backups — implementation evidence

Date: 2026-10-30 UTC. **Status: backup and isolated SQLite integrity checks PASS; complete disaster recovery NOT certified.** Code commit `821a401`.

## Architecture deployed

- Shared script: `infrastructure/backup_sqlite_state.py` invokes SQLite's online backup API, verifies `PRAGMA integrity_check` against each snapshot, includes per-file SHA-256 digests in a manifest, verifies the tar archive after writing and publishes it atomically. A file lock prevents concurrent jobs on a given destination. It ignores SQLite WAL/SHM (transactions are included via online API), cache directories, symlinks and non-allowlisted artifact suffixes.
- Control: `/usr/local/lib/venture-backup/backup-host.sh` captures selected operational SQLite and JSON/JSONL/Markdown artifacts from CEO, broker and Owner review paths to NFS `/var/backups/venture-control/sqlite-workflow`.
- Agents: same script, separate host wrapper captures Manager and Worker `level2d` state to NFS `/var/backups/venture-agents/venture-agents/sqlite-workflow`.
- Both VMs: `venture-sqlite-state-backup.service` and `.timer`; scheduled daily 04:15 UTC with randomized delay. Both `systemctl start` runs returned `Result=success`, `ExecMainStatus=0`, timers active.
- Agents installed `nfs-common`, mounted existing separate physical TrueNAS VM `192.168.0.249:/mnt/Data/epsilon` with NFSv4.2 and added an automount entry to `/etc/fstab`. Did not change Manager/Worker code or inference config.

## Test evidence

| Host | Isolated archive integrity and SQLite restore | Representative SHA-256 |
|---|---|---|
| Control | 34 files verified, 17 restored SQLite DBs `PRAGMA integrity_check=ok` | `af203151d1ac8dbccd45a48e7378c61b58980a6f7eca76d175273f07b8803f4e` (pre-timer test) |
| Agents | 15 files verified, 10 restored SQLite DBs `PRAGMA integrity_check=ok` | `0737583eb9375571c0c68b8ecd4e6655b4925842888324fdfd729fa46b990ad1` |

The tests extracted and inspected SQLite snapshots into temporary isolated directories. No recovered services were started; **cryptographic workflow signatures, exact source comparison and whole-host recovery are not yet independently verified**.

## Security and scope limitations

1. The existing NFSv4 deployment uses `sec=sys`; transport is not end-to-end encrypted by this setting. Both VMs have broad access to the TrueNAS export. Strengthen dataset ACLs, retention, protected snapshots, and encrypted transfer before considering secrets safe there. **Do not back up private signing keys, OpenBao unseal keys, or API secrets via this archive process.**
2. Snapshot coverage is restricted to selected directories and allowlisted file suffixes. It is not yet an exhaustive source-of-truth data catalog. Some non-JSON artifacts, external state, service configs, and critical secrets are outside its scope. The archive is not itself encrypted.
3. The tool tests SQLite data integrity, not application-level signed workflow chains or authorization history against pinned Ed25519 manifests. Formal Owner signature keys still need separate secure recovery validation.
4. These backups are daily; worst-case recovery-point loss can approach 24 hours or more if jobs fail. No monitored alerting, full retention verification, replication, backup immutability or measured RTO/RPO yet.
5. Independent Claude review remains pending; full isolated two-VM restore remains pending. Keep external website/payment/customer integration held until broader DR acceptance.
6. Operational observation after backup deployment: `venture-level2d-manager.service` and `venture-level2d-worker.service` active, but `venture-level2d-ceo.service` and `venture-level2c-ceo.service` reported inactive; **this audit did not restart them** and makes no claim that the CEO's continuous internal loop is active.

## Next validation

- Audit full source coverage and pinned-key manifests including artifact hashes; prove one restored signed event chain using a verifier in isolation.
- Inspect TrueNAS dataset snapshots/retention and NFS access restrictions through an authorized TrueNAS operator.
- Test a full two-VM restore from off-VM backups with no provider/payment/customer calls, then conduct independent review.
- Establish a separate encrypted Owner-controlled secrets/key recovery process, with documented rotation and revocation.
