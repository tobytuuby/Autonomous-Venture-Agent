# ADR-001: PostgreSQL Is Authoritative State

- Status: accepted
- Phase: P0.1
- Scope: venture-control only

PostgreSQL is the authoritative durable state store for the venture-control plane. Future broker, ledger, identity, lifecycle, supervisor, and governor state must be introduced through migrations and must not rely on mutable process-local state.

The P0.1 installation uses the distribution PostgreSQL package and the default local cluster. Host-level PostgreSQL access is restricted to venture-control; venture-agents must not receive database credentials or network access to PostgreSQL.

Every schema change is a reviewed migration file. Manual production schema edits are prohibited. Backups use pg_dump in custom format and must target a destination outside both venture VMs. The backup destination is supplied explicitly through BACKUP_DESTINATION; this repository does not silently select a local directory as an off-box destination.

P0.1 validation covers migration application and rollback, serializable transaction behavior for competing claims, and backup/restore equivalence once an approved off-box destination is configured.
