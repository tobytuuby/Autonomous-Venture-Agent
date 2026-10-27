# Scheduled CEO recovery and escalation review — operator guide v1.2

Implementation guide, 2026-10-27. Supersedes v1.1 scheduling/recovery guidance;
v1.0/v1.1 remain historical. No policy, phase acceptance, owner approval,
live authority, or ADV-001–ADV-049 /49 denominator changes.

## Administrative terminal resolution

A legacy STARTED cycle is ambiguous even when its decision event says provider
call failed. It can have consumed paid work. Never delete databases, edit cycle
status, reset decision rows, copy a completed response over an attempt, or change
the hour to retry. Investigate billing/provider execution outside this runtime.

`agents.ceo.queue_recovery` provides one conservative outcome:
ABANDONED_NO_RETRY. It closes the whole legacy advisory queue administratively;
it does not finish the pending assignment, supply a successor, or attest a CEO
review. The cycle and pending item remain STARTED/QUEUED in the historical DB.
There is deliberately no resume/retry/mark-success option.

After an operator chooses this terminal outcome, run as the legitimate state
owner from the approved project root, supplying the actual operator and durable
investigation reference (placeholders below are not evidence):

```sh
python3 -m agents.ceo.queue_recovery --state-dir artifacts/scheduled-ceo --operator OPERATOR_ID --reference DURABLE_INVESTIGATION_REFERENCE --paid-work UNKNOWN
```

UNKNOWN explicitly preserves uncertainty about paid work. RECONCILED is an
operator attestation tied to the reference, not independently verified billing
or a claim that no paid work happened. Neither classification permits retry.
The agent must not invent either an operator disposition or a reconciliation
reference. OS access to this trusted control-plane CLI/state must be restricted
to authorized operators; a typed actor name alone does not authenticate a human.

The CLI takes the same nonblocking runner.lock as the scheduler. It rejects
symlink/hardlink aliases, missing historical files, non-STARTED blocked states,
and any SQLite journal/WAL/SHM sidecar, requiring separate operator investigation
rather than checkpointing or removing historical bytes. It reads SQLite with
mode=ro&immutable=1 and exclusively fsyncs queue.resolution.json. The record
binds operator, reference, time, paid-work classification, every unresolved cycle
and exact SHA-256 of queue.started.json, queue.sqlite, queue.decisions.sqlite,
and queue.decisions.jsonl. Identical resolution replays; conflicts fail closed.

Every future advance checks the resolution before opening a writable queue DB.
A valid record returns QUEUE_ADMIN_CLOSED with zero requests. A partial, malformed,
aliased, or history-mismatched record returns QUEUE_RESOLUTION_DENIED. Removing
this record still leaves the original STARTED blocker: it cannot grant retry.
Privileged replacement/rollback of all local history requires external anchoring;
local hashes are corruption detection, not protection from a privileged writer.

## Independent dynamic advisory review

The pinned Studio Restock Kit packet remains the immutable input defined by
scheduled_intake.py. This is dynamic review of that packet's contents, not a
watcher for arbitrary files. The default timer now reports the escalation's
missing gate alongside legacy queue status. Intake-only still never configures
inference. No production CEO attachment, signer, worker, execution adapter,
manager handoff, finance action, or systemd configuration is added.

A separate lane can run despite a blocked legacy queue/bootstrap:

```sh
python3 -m agents.ceo.scheduled_exercise --state-dir artifacts/scheduled-ceo --escalation-only
```

With no explicit budget grant this returns ESCALATION_AUTHORIZATION_REQUIRED,
exit 3, zero requests, no CEO work. It writes inbox-status.json and preserves
status.json, the bootstrap report, and all historical queue/workflow bytes. A
normal default invocation retains the legacy queue status at the top level.

Actual advisory inference requires ALL of the following, independently of queue
abandonment:

- Existing shadow provider configuration and legitimate pre-model certification
  gate, checked through configured_provider; no fixture fallback.
- A trusted operator public key independently pinned by the deployment operator,
  never accepted from model/packet content. Pinning is a separate trust decision;
  this guide does not authorize key enrollment or configuration changes.
- An operator-signed, current, packet/configuration-bound grant authorizing exactly
  one shadow preparation request. The named budget reference must point to an
  independently checked safe worst-case remaining provider budget, accounting for
  all ambiguous earlier spending. Request count is not a dollar ceiling: this
  change adds no pricing oracle, monetary ledger, or provider-side spend cap.
  Do not issue a grant if that safe bound cannot be verified.

No such grant, key pinning, or verified remaining budget was supplied for the
current VM. The escalation itself explicitly opens no inference cycle. Do not
create a grant or infer authority from this implementation, fixtures, missing
environment variables, or an operator name. An authorized external operator
process must establish these gates first; no runtime signer is provided.

Once independently authorized, the control-plane operator may pass existing
protected provider environment and project-contained grant/public-key files:

```sh
python3 -m agents.ceo.scheduled_exercise --state-dir artifacts/scheduled-ceo --gate-file infrastructure/venture-ceo-kernel-gate.runtime.json --escalation-only --escalation-grant GRANT_FILE --operator-public-key PINNED_OPERATOR_PUBLIC_KEY_FILE
```

The key file contains the 32-byte Ed25519 public key in hex, never a private key.
The grant is exactly `{ "grant": {...}, "signature": "HEX" }`, signed over
canonical UTF-8 JSON (sorted keys, compact separators, no NaN). Exact grant fields
are grant_id, operator, item_id, packet_hash, scope=SHADOW_PREPARATION_ONLY,
configuration_fingerprint, maximum_requests=1, budget_reference,
reconciliation_reference, issued_at and expires_at. Identifier/text bounds are
executable in scheduled_escalation.authorize; validity must be timezone aware,
current and at most 24 hours. The configuration fingerprint is from the existing
CEOAgent with scheduled_escalation.SYSTEM, advisory_only=True and
runner_version=scheduled-escalation-v1, using the actual configured provider.
Signature verification establishes the pinned operator's attestation, not remote
billing truth, human conversation, or provider identity.

The scheduler lock serializes all lanes. Supplying a grant isolates the entire
tick from bootstrap/legacy queue work, even if validation fails. Before any ack,
decision writes, or network dispatch, it exclusively fsyncs escalation.attempt.json
with the signed grant, key hash and packet binding. It makes at most one tool-free
CEOAgent.shadow_decide call, durably retaining lineage in separate
escalation.decisions.sqlite/jsonl. Imported/partial decision state is denied.
Any crash, invalid response, IO failure, or transport error after reservation
blocks automatic inference permanently for this intake item, across restarts,
hours and different grant IDs. Never delete that marker to retry.

A successful response must match the existing exact validate_review schema,
pinned packet/item and manager-venture-001, with PREPARATION_ONLY scope. It is
stored verbatim as untrusted advisory review with
configured_provider_not_independently_verified provenance. Summary fields report
one request and ceo_work_performed=true only for that invocation's recorded
advisory work. Existing review replay reports zero requests/false new work.
No response is invented to complete a failed attempt. A crash between model
response and inbox commit conservatively blocks automatic recovery; a committed
inbox review replays without calling inference, even if status publication failed.

REVIEWED is not HANDOFF_READY, HOLD or DENIED, even when the review recommends
one of them. A separate authenticated CEO receipt under the existing inbox
protocol is still required, with trusted CEO key configuration outside this
change. No operator budget grant can substitute for that CEO receipt, and neither
receipt bypasses owner approval, venture workflow signatures, or live gates.
No manager/worker execution is performed. Response schema validation proves shape
and binding, not business quality, truth, safety of text instructions, remote
model identity, billing, or independently verified inference.
