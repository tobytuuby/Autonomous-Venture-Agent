# P1-04 C4 coordinated maintenance — synthetic procedure v1.0

Baseline main: b4b38aed55249536ff72e00043239a5d4a25d2fd.
Stage6 **DENY**; deployment_allowed=false; resume_verified=false.
This source/test increment grants no deployment, CEO, venture or capital authority.
It extends the existing deployment script; there is no coordinator service.

## Executable synthetic sequence

Run the project-local fixture tests:

```sh
python3 -B -m unittest -v tests.test_coordinated_maintenance_c4
```

The functions in scripts/level2d_acceptance_deploy_control.py accept only a
direct project child named c4-fixture-*. They contain no live service adapter.
This path restriction prevents accidental selection of an installed tree; it
is not a security boundary against an operator who can alter this checkout.

1. Review an exact immutable plan digest before entering maintenance.
   Read-only preflight bounds each inventory to 128 files, each file to 1 MiB
   and total bytes to 4 MiB. It rejects unsafe paths, symlinks, hardlinks,
   unstable files, changed baseline, incomplete participants or prerequisites.
   It creates no controls. A preflight refusal leaves existing controls untouched.
2. Require Control CEO/broker and Agents Managers 1–3/Workers A–C explicitly.
   Every (host, service UID) group pins one private C1 control and active inode;
   different groups cannot share a control. Gates must already exist. Frozen
   prerequisites pin trust, signed scope/quota, timers, external writers and
   source/installed/loaded identity observations. The synthetic observations
   are fixtures, not claims of live attestation or independently reviewed trust.
3. Persist CLOSED on every group before waiting. Acquire local role drains,
   then the broker group, with one shared bounded deadline. Already admitted
   actions finish under their leases; fresh admissions fail. A failed close,
   drain, timeout or crash cannot create an acceptance receipt.
4. After all drains, recheck immutable baselines and take exhaustive flat state
   byte/hash/owner/mode/inode snapshots, including SQLite files and sidecars.
   Final responses written by slow actions must exist in the declared inventory.
   Unknown sidecars invalidate coverage. Require COMPLETE plus DURABLE response.
   Pending, lost or unknown responses HOLD; there is no inference retry.
5. Back up only pinned .py code under code/Control or code/Agents, in sorted
   path order, with fsync of backup files and directories before replacement.
   Backup index N maps to sorted(plan.updates)[N]; the reviewed baseline pins
   the original hash. Compile candidates, atomically replace, then verify state
   bytes/identity and every unchanged frozen prerequisite. No state is restored.
   Failure restores applied code only and attempts closure of all controls.
6. Write a CLOSED attestation containing plan digest, state hashes, updated
   frozen snapshots and gate pins. Context exit keeps controls CLOSED.
7. Independent review must supply the exact attestation digest to the separate
   release_synthetic_after_attestation call. Revalidate state, code and gate
   pins and acquire all drains again before explicit C1 release. Drift or
   release failure leaves/recloses all accessible controls. Storage failures
   require operator HOLD; successful closure is never inferred from an exception.

The fixture models two host namespaces using separate directories and the
runner UID. It does not independently execute on two machines or validate
different real service users. Real C1 flock admission/drain, process death,
fresh-process refusal, local SQLite bytes and Ed25519 signatures are exercised.
The role and broker regression suites retain actual inference-intent, quota,
signed-transition and completed/ambiguous recovery checks. No authority logic
or ambiguous recovery behavior is weakened.

## Staged production bootstrap — currently NO-GO

The user reports active real Managers without gates and an installed broker
without C1. This increment did not inspect or operate those installations.
A source gate cannot retroactively cover those processes. A broker restart,
a new CLOSED file, or a Manager config edit alone is not quiescence proof.

The following is the required future operator procedure, **not an instruction
to execute production now**. Existing Stage6 must be satisfied through its
separately reviewed implementation/evidence workflow first; there is no new
approval gate and no flag to bypass its DENY.

1. Prepare one owner-reviewed, hash-pinned maintenance record: exact host IDs,
   service UIDs, units/instances/cgroups/PID start identities, all role entrypoints,
   timer/cron/renewal/backup/API/manual writers, private state roots and complete
   file/sidecar inventories, public trust/scope/quota pins, installed/source/loaded
   module hashes, proposed code allowlist and backup/rollback mapping. Record
   mandatory GitHub/Claude review evidence. No private keys enter the record.
2. Obtain a **separate safe manual quiescence proof** for legacy participants
   before adoption. The responsible operator must prevent new scheduling and
   new manual/API work on both hosts, account for timer jobs/external writers,
   and prove all in-flight actions ended at durable boundaries. Use existing
   read-only proof APIs and identity observations; never POST a reconciliation
   or retry ambiguous work to manufacture proof. If existing evidence cannot
   prove an action completed, HOLD. Do not kill an uncertain process and call
   its work drained. Request a narrowly scoped owner decision only where safe
   quiescence requires an operational action beyond existing authority.
3. Under that independently established exclusion, record byte/hash snapshots
   and verified signed state/quota/trust baselines. Provision persistent CLOSED
   C1 controls as each service UID, private directory 0700/files 0600, with
   active files empty and inode pins recorded. Adopt the exact same host/UID
   control in every writer config; omission preserves legacy behavior and
   therefore invalidates coverage. Keep manual exclusion throughout adoption.
4. Back up code only. Install reviewed C1/C3A dependencies and configs in the
   existing components without starting inference. A separately authorized,
   safe restart may load them only after steps 1–3 and Stage6 permit it.
   Starting a role with a CLOSED control must refuse before constructors/writes.
   Verify installed hashes separately from loaded process hashes/UIDs/configs.
   No source hash or synthetic transport proves the latter.
5. Re-establish local drains and broker CLOSED/no-leases proof on both hosts.
   Join fresh writer inventories, identity evidence and unchanged byte/hash
   snapshots in one attestation. Check pending/durable-response proof without
   retry; preserve signed state and all consumed quotas. Keep timers/external
   writers excluded. An absent/incomplete proof means HOLD with controls CLOSED.
6. Independent release occurs only after that exact attestation is reviewed
   under the existing authority workflow. Release each existing control
   explicitly, with a recorded order and post-release observations. A failed
   release must close the cohort again and retain manual exclusion.
   Never automatically release on successful install, rollback or process exit.

If adoption crashes, retain CLOSED/manual exclusion; identify which code
replacements occurred using the reviewed sorted mapping and backup hashes.
Restore code only if safely authorized, re-attest installed/loaded identity and
unchanged state, then seek independent release. Never restore a signed journal,
quota ledger, trust or pending intent from a maintenance backup. A partial
rollback or storage failure remains unresolved HOLD.

## Evidence and decision

Raw per-case outputs and process metadata are in
tests/acceptance-evidence/p1-04-c4-20261106/. These supplement the existing
ADV-001–ADV-049 universe and unchanged /49 denominator.

Classification: local synthetic execution only. Production two-host acceptance,
current installed/loaded identity, manual legacy quiescence and independent
GitHub/Claude review remain unverified. Owner-review digests in fixture tests
model exact review binding; the helper is not an owner authentication system.
An uncooperative privileged writer or concurrent independent release operator
is outside the cooperative fixture proof. Operators must serialize maintenance
and release under the reviewed procedure.

Local decision: synthetic source acceptance subject to the recorded test
results; operational deployment remains denied. No live controls, ledgers,
services, real CEO, provider calls, deployment or capital actions were used.
The preexisting dirty deployment_pause.py SHA256 remains
4aa2fa78cba1d59df098d3127d7ef2c4bc0f2bf713855246bebd2823447128e9.
