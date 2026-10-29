# Live system inventory (observed 2026-10-29)

**Evidence classification:** service names and paths observed live, not an exhaustive asset scan. Check `/etc/systemd/system`, linked units and runtime configs before restore. Do not store sensitive unit EnvironmentFile values in this repository.

| Boundary | Source and durable paths | Main systemd components |
|---|---|---|
| Control VM (`venture-control`) | Source workspace `/home/epsilon/venture-control-workspace`; runtime `/usr/local/lib/venture-ceo-level2c`, `/usr/local/lib/venture-control-broker-level2c`, `/var/lib/venture-ceo`, `/var/lib/venture-control-broker` | `venture-level2d-ceo.service`, `venture-level2c-ceo.service`, `venture-control-broker-mtls.service`, `venture-control-bridge.service`, control broker/tunnel |
| Agents VM (`venture-agents`) | Workspace `/home/epsilon/venture-agents-workspace`; runtime `/usr/local/lib/venture-manager-level2c`; state `/var/lib/venture-manager`, `/var/lib/venture-worker` | `venture-level2d-manager.service`, `venture-level2d-worker.service`, `venture-level2c-manager.service` |
| Owner review (Control) | Runtime `/usr/local/lib/venture-review`; local state `/var/lib/venture-review/inbox/reviews.sqlite` and a copied discovery snapshot; private credential file `/etc/venture-review.env` | `venture-owner-idea-review.service`, `venture-owner-feedback-publish.timer` |
| CEO discovery | `/usr/local/lib/venture-ceo-level2c/artifacts/venture-discovery/discovery.sqlite`, initial result JSON and advisory `owner-feedback.json` | One-shot provider discovery cycle `initial-20261029`; **no recurring discovery service proven** |
| CTKFamily website | `/var/www/ctkfamily`, own deployment/repository and authentication | Not yet connected to the Control Owner API: no completed Option B production bridge |
| Finance | `kernel/finance/finance.py`, request-only workflow; historical draft specs | Real PayPal / capital allocation **not activated or verified** |

## Explicit state worth recovering

- Signed hierarchy transitions and broker workflow SQLite databases including `-wal`/`-shm` as appropriate for consistency.
- Separate CEO, Manager and Worker inference intent/completion SQLite files (including possibly ambiguous provider calls), artifact revisions and provenance.
- CEO discovery proposals; Owner review decisions, their exact proposal digests, and the advisory feedback export.
- Role-pinned Ed25519 trust manifests, service certificates and full CA/renewal configuration; OpenBao data and unseal/recovery details held securely outside Git.
- Financial policy/ledger checkpoints, Postgres storage and backup manifests; do not equate synthetic test ledgers with live deposits.
- Unit definitions, environment-file *locations*, filesystem ACLs, ownership/setgid, scheduled jobs, DNS, VM/network/firewall routing, service account identities and working directories.

## Timers observed

Control: `venture-owner-feedback-publish.timer`, `venture-ceo-exercise.timer`, `venture-control-ledger-checkpoint.timer`, `venture-control-postgres-backup.timer`, `venture-level2d-cert-renew-control.timer`, plus existing preparation/handoff timers. Agents: `venture-level2d-cert-renew-agent.timer` and `venture-level2d-cert-renew-worker.timer`. Verify current units using `systemctl list-timers --all` and avoid enabling duplicate older services.

## Warning: known live drift

The Control worktree included pre-existing modified/untracked files at this snapshot, including `agents/ceo/service_identity.py`, `kernel/synthetic_venture_store.py`, `kernel/venture_admission.py`, `tests/test_owner_approval.py` and untracked hierarchy components. **Do not `git clean`, `reset --hard`, or equate a clean clone to the deployed runtime.** Capture diffs securely before any machine rebuild; never blindly promote unreviewed dirty files to production.
