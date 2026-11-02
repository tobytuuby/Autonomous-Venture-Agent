# Legacy internal research Worker routing recovery v1.0

Date: 2026-11-02. Implementation amendment authorized by the owner's narrow legacy
Client Document Checklist recovery instruction. Applies to the existing signed
PREPARATION_ONLY hierarchy, not live operations. The bounded internal research
continuation policy v1.0 and operational viability project plan v2.4 remain binding.

The CEO may append one `recover_legacy_worker` command to a signed
`WORKER_PENDING` internal research workflow with no decomposition, the retired
`service-worker` scope, `service-manager`, one approved objective, seed 1, budget
at most 5 and at least three effort units remaining. All three current Worker
trust pins must exist. The broker rechecks the complete authoritative Owner
proposal digest and handoff against the existing Owner approval snapshot.
A changed/revoked/ambiguous approval fails closed; no repeated Owner approval
is introduced for the exact already-approved research.

The sole state change is to `MANAGER_PENDING`. Scope, scope hash, version,
used effort, handoff, signed evidence, round/session identity, prior audit events
and inference ledgers are retained. The repair is a routing correction, never a
new research round, correction-version allowance, budget grant or paid retry.
The command payload admits only a bounded reason, not replacement scope or budget.
Signed reconstruction checks the same routing preconditions on journal reopen.
Historical single-Worker genesis/delegation and other signed events remain
readable. New broker delegation to the retired Worker is denied.

The broker reads retained proposal-wide reservations and requires room for three
new assignments under four per round and twelve total. All failed/ambiguous
legacy reservations remain charged. Missing/unverifiable accounting fails closed.
A repair itself makes no provider call and changes no reservation. Existing Worker
policy, request identity, pre-execution reservation, execution deduplication and
central ProviderQuota continue to govern every subsequent call; legacy requests
are never retried or reissued by recovery. Manager must propose A/B/C and CEO must
approve their decomposition before active Workers execute.

The existing CEO research daemon detects this shape on periodic polling and
submits one signed command bound to the exact snapshot revision/hash. Restart
and response loss are resolved by rereading signed state. Exact accepted replay
returns its historical receipt; conflicting or stale attempts cannot append.
Unavailable allowance or invalid lineage is reported through the existing daemon
error path and leaves the workflow unchanged. This amendment deliberately grants
no generic resume, security-clear, terminate, launch or capital permission.

Validation and review evidence is recorded under
`tests/acceptance-evidence/legacy-worker-recovery-20261102/`.
Tests use isolated keys, signed journals and fake providers. They do not prove
production acceptance, live reachability, deployment or recovery of the named
runtime workflow. ADV-001–ADV-049 and the /49 denominator are unchanged.
