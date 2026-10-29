# Read-only live operational checkpoint — 2026-10-29 UTC

Source: direct systemd inspection of Control VM during creation of this documentation set. This is an observation, NOT proof of off-host backup or successful clean-room restoration.

| Unit | Observed status |
|---|---|
| `venture-control-postgres-backup.service` | `Result=success`, `ExecMainStatus=0`, last exit `2026-10-29 03:25:53 UTC` |
| `venture-control-ledger-checkpoint.service` | `Result=success`, `ExecMainStatus=0` |
| `venture-level2d-cert-renew-control.service` | `Result=success`, `ExecMainStatus=0` |
| `venture-owner-idea-review.service` | Previously verified active and bound only to `127.0.0.1:8791`; unauthenticated 401, authenticated 200 |
| `venture-owner-feedback-publish.timer` | Previously verified active and CEO advisory export readable |

## Limits

A successful backup systemd unit is *not* proof that its output exists off-host, that an encrypted archive is intact, or that all newer databases are included. No credentials, backups, or host disk images were copied into this repository. This checkpoint is a dated reference to distinguish the historical live state from later DR assumptions.

Review source: `docs/disaster-recovery/OPEN-GAPS.md` (DR-01 to DR-10). Recheck on every recovery event; do not treat this checkpoint as current forever.
