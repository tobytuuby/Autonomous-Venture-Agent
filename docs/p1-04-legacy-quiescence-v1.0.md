# P1-04 Legacy Quiescence and Initial Admission Runbook v1.0

**Status: prepared for operator review; not an authorization to cut over.**  
**Scope:** one-time bootstrap from the currently installed legacy AVA processes to the already implemented P1-04 admission and coordinated maintenance controls. Uses the existing Control and Agents VMs, existing systemd services/timers, broker, CEO, Managers and Workers, and the existing C1/C3A/C4 mechanisms. It adds no service or maintenance architecture.

## Safety invariants

- Keep the two ambiguous provider executions on HOLD. Do not resubmit, retry, reset quotas, rewrite their pending records, or treat a missing response as a failure.
- Do not deploy, restart, stop, mask, or reconfigure a production service until the pre-cutover checks in this runbook pass and the maintenance window is explicitly opened by the owner/operator.
- Do not infer drain from an empty queue, sleeping process, absence of a writable file descriptor, or a synthetic C4 result.
- Preserve signed workflow, ledger, reservation, provider-intent, and review bytes. A backup is evidence only after its integrity and restore procedure are verified.
- On any unknown, changing inventory, PID identity change, provider uncertainty, or failed check: leave services and state untouched, record HOLD, and do not resume automatically.

## Current live inventory basis

Read-only observations collected on 2026-11-06 are non-atomic samples. They identify participants for the cutover; they do not prove exclusion or quiescence.

### Venture-Control

Active state-changing or potentially state-changing units observed:

- `venture-owner-research-ceo.service` — CEO poller; PID 288443; working directory `/usr/local/lib/venture-ceo-level2c`; no deployment lock configured.
- `venture-control-broker-mtls.service` — shared broker; PID 288442; working directory `/usr/local/lib/venture-control-broker-level2c`.
- `venture-owner-api.service` — Owner API; PID 219355.
- `venture-owner-idea-review.service` — idea-review worker; PID 2941584.

Active timers/transient timers observed include:

- `venture-owner-research-kickoff.timer`
- `venture-owner-feedback-publish.timer`
- `venture-preparation-control.timer`
- `venture-preparation-broker.timer` (transient)
- `venture-authenticated-handoff.timer` (transient)
- `venture-control-ledger-checkpoint.timer`
- `venture-control-postgres-backup.timer`
- `venture-level2d-cert-renew-control.timer`
- `venture-sqlite-state-backup.timer`

The CEO/broker inventory found two PENDING provider-intent files, one PENDING remote execution and one PENDING Worker execution. These are treated as the two known ambiguous executions and their related records; counts are not a signature or outcome verification.

### Venture-Agents

Active Managers observed:

- `venture-level2c-manager.service` — PID 1257; legacy `preparation_exchange` entrypoint.
- `venture-level2d-manager.service` — PID 1259; legacy `hierarchy_service` entrypoint.
- `venture-owner-research-manager.service` — PID 1260; legacy `hierarchy_research_daemon` entrypoint.

The actual Worker instances `venture-level2d-worker@worker-a.service`, `@worker-b.service`, and `@worker-c.service` were inactive at the sample. Legacy `venture-level2d-worker.service`, `venture-owner-research-worker.service`, and template instances `@a`, `@b`, `@c` were also enumerated. Inactive/disabled units do not exclude manual starts, direct invocation, or alternate identities.

Active timers observed include:

- `venture-level2d-cert-renew-agent.timer`
- `venture-level2d-cert-renew-worker.timer`
- `venture-sqlite-state-backup.timer`

The backup and certificate scripts are root scheduled writers or service restarters and must be included even when their service unit is currently inactive.

### Writers outside the named AVA units

The host-level boundary must also enumerate system and user systemd units, transient units and jobs, cron and user crontabs, `at` jobs, direct processes, open writable descriptors, service-account access, ACLs, sudo/root access, the bridge account, remote operators, and any process able to write the protected state or restart a participant. The prior host scan saw 140 privileged or role-UID processes; that count did not identify a durable exclusion. Root and authorized operators remain potential writers unless the maintenance window explicitly constrains their actions.

## Required pre-cutover evidence

Collect fresh evidence on both hosts in the same maintenance window. Keep raw output private where it can contain local paths or identifiers; publish only sanitized evidence and hashes.

1. **Pin the build.** Record the exact tested commit and per-file hashes for the broker, CEO, Manager, Worker, admission, and coordinator modules. Confirm those exact bytes are present in the deployment package on both hosts. Do not use a dirty working tree as a deployment source.
2. **Enumerate units and jobs.** On each host, inventory loaded and installed service/timer units, templates and every instantiated worker identity; enumerate transient units, systemd jobs, timer schedules, cron, user crontabs, and `at` jobs. Reconcile every discovered unit/process to a named role, state root, and planned treatment. Any unclassified writer blocks cutover.
3. **Enumerate protected state.** Map all Control and Agents workflow, ledger, outbox, reservation, execution, Manager, Worker, CEO review, provider-intent, and backup stores to their writer identities. Include WAL/SHM/journal sidecars, symlinks, ACLs, mount permissions, and any state store outside the expected roots. Unknown or unreadable stores block cutover.
4. **Verify the HOLD records.** Use existing read-only evidence/reconciliation paths to bind each ambiguous execution to its exact request digest, reservation, provider intent, and signed workflow state. Do not invoke the provider. If signed binding or outcome remains uncertain, preserve HOLD and do not continue.
5. **Prove current activity can drain.** For every active CEO/Manager/Worker/broker participant, use an existing application acknowledgment or existing broker lease/drain proof to show no accepted operation remains in flight. Verify final local state writes are complete and signed chains/ledger are consistent. Logs, process sleep, queue counts, or descriptor samples alone do not satisfy this check. The legacy installed entrypoints currently have no demonstrated shared pause/drain acknowledgment; if no existing component can produce this evidence, this procedure stops here.
6. **Protect recovery.** Take consistent, SQLite-aware backups of every required store only after its writer is proven quiescent. Verify hashes, signed lineage, and the existing restore procedure in an isolated copy. Preserve the pre-change unit files, configs, file ownership/modes/ACLs, and installed-code manifests.
7. **Record the maintenance lease.** Record the approved window, operator, exact participant set, pinned service identities, state roots, backup hashes, and hold set in the existing evidence path. No new AVA authority or synthetic receipt is created.

## Controlled cutover sequence

This sequence is conditional on all pre-cutover evidence passing. It is not executable on the current observations.

1. Stop new work at the existing Control ingress: Owner API mutations, idea-review intake, kickoff, feedback publication, handoff, preparation-control and preparation-broker schedules. Confirm systemd has no queued/transient job capable of recreating them. Preserve the Owner UI's existing evidence; do not create approvals.
2. Close the existing broker admission path using the already implemented C1 maintenance mechanism. Verify its exact pinned inode/identity, admission-closed acknowledgment, and drained leases. If the installed broker lacks C1 or the acknowledgment is not durable, stop; do not substitute a service stop or synthetic test result.
3. Request and verify an existing application-level drain acknowledgment from the three Agents Managers and every actual Worker instance. Prevent manual/template invocation under the maintenance window. Keep backup and certificate jobs held only for the bounded window after their effects and resume plan are documented.
4. Wait for each accepted operation to reach a durable, verified terminal state. Any ambiguous provider request remains pending and held. No retry, re-execution, quota change, or fabricated terminal status is permitted.
5. Recheck on both hosts: no unclassified writer, no systemd job, no state-changing process beyond explicitly allowed maintenance observers, no open write descriptor to protected state, no changed PID/unit identity, and no store changing across two bounded observations. Verify every protected root and signed lineage.
6. Only after that acknowledgment, keep the broker admission closed and install the exact pinned per-role controls from the tested package. Back up each existing file before replacement. Use the existing role-specific controls for CEO, Manager and Worker and the existing broker C1 boundary; do not create a second coordinator.
7. Verify installed hashes, owner/mode/ACL, service identities, configs and load path before restarting. Restart in dependency order with admission still closed: broker, Agents Managers, Workers only when required, then CEO and Owner/API schedulers. Verify loaded code through existing attestation mechanisms; disk hashes alone do not prove loaded bytes.
8. Run the existing coordinated pause/drain/restart/rollback/resume acceptance using isolated synthetic work only. Verify signed-state hashes and ledger integrity before and after. Exercise rollback from the verified backups while keeping the broker closed; prove recovery before resuming eligible work.
9. Resume only work whose signed state is verified and whose outcome is unambiguous. Keep the two provider executions on HOLD through acceptance. Do not reset quotas.
10. Re-run the read-only Stage 6 preflight on the joined, current evidence. A NO-GO/HOLD, incomplete inventory, missing independent review, or unresolved HOLD binding leaves admission closed and P1-04 open.

## Current disposition

**HOLD — no legacy quiescence acknowledgment exists.** The installed Managers do not have the new admission integration, the installed broker/CEO are not proven to share the tested admission controls, and no existing live component currently demonstrates a durable cross-host drain. The read-only inventories also do not verify loaded Python bytes, signed state, or the two provider outcomes.

Accordingly, this runbook preparation performs no production service stop/restart, timer change, config edit, file replacement, state mutation, provider call, retry, quota reset, or resume. The next execution step is the operator-reviewed pre-cutover evidence collection above; it may proceed only through existing controls and only while every unknown remains fail-closed.
