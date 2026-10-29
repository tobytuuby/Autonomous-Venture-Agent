# Recovery runbook — human-led, preparation-only

**This is an ordered recovery checklist, not a verified automated full-host restore.** Must be followed alongside `START-HERE.md`, `SYSTEM-INVENTORY.md`, and `BACKUP-COVERAGE.md`. Commands below are *inspection commands*; do not execute unreviewed destructive restoration commands from an incident chat.

## Phase 0: Containment and evidence

- [ ] Human Owner declares incident and scope (Control/Agents/webserver/credential/storage/network). Disable live commercial authority, financial execution and external outreach independently of AI controls.
- [ ] Record UTC timestamp, incident ticket, surviving host identities, expected original Git commits and backups, last signed workflow sequence and last transaction reconciliation.
- [ ] Preserve affected disks/snapshots and journal trails. Do not restart or purge compromised state prior to capture; quarantine compromised credentials and revoke trust as needed.
- [ ] Confirm known-good off-host Git and encrypted backup sources, recovery credentials and independent Owner keys. **Never paste private signing keys or tokens into ChatGPT, Claude, public Git, or logs.**

## Phase 1: Build hosts under deny-by-default

- [ ] Rebuild isolated Control and Agents machines using Owner-controlled baseline image. No production outbound business authority, no payment credentials, and no automatic paid inference services yet.
- [ ] Restore OS user/group identities and file ACLs only from approved validated configuration; verify `/etc/systemd/system`, Linux package dependencies, Python venv and runtime permissions.
- [ ] Clone trusted pinned commit from `tobytuuby/Autonomous-Venture-Agent`; compare archived deployed versions and protected dirty worktrees before choosing runtime packages. Avoid enabling legacy and Level2D services simultaneously.
- [ ] Reestablish restricted network/firewall, DNS, service identity, CA roots and mTLS with current trusted pinned keys; rotate certificates and keys if compromise cannot be ruled out. Never reuse a revoked key.
- [ ] Recover OpenBao only from verified separately held encrypted backups and authorized recovery custodians; test seal/unseal and renewal in a nonproduction isolated environment.

## Phase 2: Restore data with state frozen

- [ ] Verify manifest, storage source, encryption, archive hashes, UTC snapshot boundary and completeness, including SQLite WAL consistency and Postgres point-in-time needs.
- [ ] Restore financial ledgers and Postgres checkpoint before any financial service is restarted; reconcile externally with payment provider / bank, noting uncertain transactions.
- [ ] Restore Control broker workflow DB and signed transition chain, CEO inference DB, artifact versions and centrally reserved provider usage ledger. Run signature/actor/sequence/evidence and hash-chain verifiers against pinned trust manifests.
- [ ] Restore Agents Manager and Worker inference DBs and work-product artifacts. Pair inference intents with completion evidence; mark `PENDING` / interrupted paid requests `AMBIGUOUS` and **do not automatically retry**.
- [ ] Restore owner idea review decisions, discovery records, proposal SHA-256 digests and advisory feedback. Recompute proposal binding, catch stale revisions, refuse overwrite of signed Owner receipts.
- [ ] Validate database integrity (`PRAGMA integrity_check` for SQLite), ownership and directory ACLs before enabling any service.

## Phase 3: Limited service recovery (no authority promotion)

- [ ] Start secrets/certificate validation and read-only storage verification first; then broker mTLS and internal bounded hierarchy services **only** with `PREPARATION_ONLY` and all money / customer / external authorization flags false.
- [ ] Inspect unit definitions and dependencies with `systemctl cat`, `systemctl is-enabled`, `systemctl is-active`, `systemctl list-timers --all`; keep timers disabled until restored queues and credentials reconcile.
- [ ] Verify time sync, clock skew, mTLS handshake, pinned Ed25519 role identities, broker deny cases, duplicate/replay denial, startup after process restart, and no inferred owner approval.
- [ ] Verify dedicated Owner idea review remains bound to loopback; unauthorized request returns 401; legitimate Owner session reads only expected proposals. Feedback timer exports advisory decisions, **not** signed authorization.
- [ ] Verify cert renewal for CEO, broker, Manager and Worker by planned expiry, with Owner-held contingency to renew/revoke. Last recorded historical expiry was 2026-11-12; those dates are NOT sufficient for a later restore.
- [ ] Reconcile all provider calls and central reserved usage. Do not fire new paid model requests while outcome of old intents is ambiguous.
- [ ] Test no capital release, no PayPal live execution, no production launch, no customer contact, and no cross-role approval impersonation.

## Phase 4: Independent verification and authorization

- [ ] Run scoped deterministic test suites and an isolated nonfinancial synthetic end-to-end CEO → Manager → Worker → Manager → CEO review, verifying signed revision chain.
- [ ] Produce a recovery evidence packet: source commit, OS/image hashes, backup manifest, database validation, trust manifest, timer/service status, denied-authority tests, restored latest event IDs, reconciling differences, and unresolved gaps.
- [ ] Independent reviewer examines recovery evidence and explicitly identifies untested areas. Human Owner makes written restart/approval decision; reviewer or AI CEO cannot authorize Owner financial actions.
- [ ] Only then consider enabling bounded **discovery/research** after Owner authorization. Commercial and financial operations remain separately gated.

## Useful read-only triage commands (run on applicable host)

```bash
hostname; date -u; git rev-parse HEAD; git status --short
```

```bash
systemctl list-unit-files 'venture*' --no-pager
```

```bash
systemctl list-timers --all --no-pager
```

```bash
systemctl --failed --no-pager
```

```bash
sudo systemctl cat venture-level2d-ceo.service
```

```bash
sudo systemctl cat venture-level2d-manager.service
```

```bash
sudo systemctl cat venture-level2d-worker.service
```

Never print the contents of secret environment files. Avoid unscoped journal output that might include credentials. Maintain a dated recovery log of every action and outcome.
