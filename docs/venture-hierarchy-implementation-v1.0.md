# Venture hierarchy implementation plan and operator guide v1.0

2026-10-27. Local preparation increment; governing
[policy v1.0](venture-hierarchy-policy-v1.0.md). Baseline main `8b85728`.
This core capability increment supplements
[core synthetic orchestration v1.1](core-synthetic-orchestration-plan-v1.1.md)
without changing phase status, prior acceptance or any historical specification.

## Implemented scope and validation plan

1. Reuse the existing escalation inbox's path constraints, private SQLite setup,
   transaction, event append and read primitives in a separate workflow database.
2. Add `agents/ceo/venture_workflow.py`: explicit signed role transitions,
   preparation scope/version/effort gates, review correction, hold/security/stop,
   immutable evidence refs, idempotency and request-only finance.
3. Add `tests/test_venture_workflow.py`: synthetic positive paths, improvement,
   premise rejection, owner rejection/correction, bypass attempts, expiry, budgets,
   crash rollback, concurrent retry and audit corruption.
4. Run focused inbox/owner/workflow regressions and full unittest discovery.
   Preserve raw scenario output and an implementer decision log; classify it as
   supplemental synthetic/local evidence. Do not claim ADV recertification.
5. Verify owner-file fingerprints and diff whitespace; commit/push only this
   increment's explicit files. No service, systemd or deployment work.

## Studio Restock Kit: what the operator sees

Studio Restock Kit (`venture-001`) is still an unapproved pilot. The concrete
preparation task is “Draft a tenant isolation and durable CRUD acceptance plan.”
An example scope is:

```json
{
  "mode": "PREPARATION_ONLY",
  "manager_id": "manager-venture-001",
  "worker_id": "worker-studio-plan",
  "tasks": ["Draft Studio Restock Kit tenant isolation and durable CRUD acceptance plan"],
  "budget_units": 5,
  "seed_cents": 10000
}
```

The manager delegates preparation, the worker submits a plan with one unit of
declared effort and immutable artifact digest, and the manager requests
improvement if recovery/tenant tests are missing. The worker submits a corrected
artifact under a **new reference name**, consuming two further units. Manager
approval sends the package to CEO review. CEO approval sends a recommendation to
the owner; it does not approve for the owner.

If the manager rejects the premise (for example, the proposed product cannot
satisfy tenant isolation within the stated task scope), the workflow waits in
CEO_REDIRECTION. The CEO must issue a reasoned next-version scope before
delegation can resume. If the owner rejects the reviewed proposal, finance stays
blocked. The CEO must correct it as a new version and repeat every review.

A human-approved package may receive a CEO request for up to 10,000 cents.
The result reads FINANCE_REQUESTED with `status=REQUEST_ONLY`,
`money_released=false` and `execution_performed=false`. There is no payment
button or dispatch capability. Before any future operational work, the
canonical owner-admission policy and all other gates still apply independently.

## Safe local demonstration

From the approved project root, this executable example uses temporary databases
inside `artifacts/` and ephemeral synthetic signatures, and cleans up afterward:

```sh
python3 -m unittest tests.test_venture_workflow.WorkflowTests.test_positive_improvement_final_owner_and_finance_request_only -v
python3 -m unittest tests.test_venture_workflow.WorkflowTests.test_owner_rejection_correction_cannot_skip_gates -v
python3 -m unittest tests.test_venture_workflow.WorkflowTests.test_premise_rejection_requires_ceo_new_version_and_all_reviews -v
```

These examples do not process the real pilot, obtain a human decision, contact
a model/provider or execute a manager/worker.

## Trusted integration API

There is deliberately no signing or enrollment CLI. A future trusted operator
adapter supplies pinned public keys; agents cannot supply/replace these pins.
The CEO pin must equal the key already trusted by the escalation inbox.
Never connect raw model output to a signer.

```python
from agents.ceo.escalation_inbox import EscalationInbox
from agents.ceo.venture_workflow import VentureWorkflow

# Trusted application configuration, never model/request data:
# pins = {actor_id: (role, raw_ed25519_public_key_bytes), ...}
# CEO and owner must have distinct pins; human owner signing stays out of band.
inbox = EscalationInbox("artifacts/ceo-escalations/inbox.sqlite",
                        ceo_public_key=ceo_public_key)
workflow = VentureWorkflow("artifacts/ceo-escalations/workflow.sqlite", actors=pins)
try:
    # command/signature are independently supplied signed receipts.
    # A real verified HANDOFF_READY record is mandatory; no fallback decision.
    result = workflow.create(create_command, create_signature,
                             inbox=inbox, item_id="studio-online-20261027")
    current = workflow.read(result["id"])
    # For each subsequent externally authorized signed review/control receipt:
    result = workflow.apply(command, signature)
finally:
    workflow.close()
    inbox.close()
```

The snippet documents dependencies rather than inventing pins or receipts; it is
not a self-contained auto-approval script. Use a new separate workflow database,
never a scheduler, pilot or owner-admission database. No actual integration of a
scheduler or signer is claimed.

## Exact command contract

Canonical signing bytes use `canonical(command).encode()`: sorted keys,
compact JSON separators and no NaN. Signatures are hex Ed25519 signatures.
Every command has **exactly** these fields:

| Field | Meaning |
| --- | --- |
| workflow_id, request_id | bounded ASCII IDs; request ID globally unique in this DB |
| actor_id, role | exact pinned actor and role |
| origin | human_out_of_band for owner; control_plane otherwise |
| action | an allowed action in the policy transition table |
| revision | current integer revision; 0 on creation |
| previous_hash | `hashed(current_snapshot)`; GENESIS on creation |
| version | current integer proposal version; 1 on creation |
| scope_hash | `hashed(current_scope)` |
| evidence | 1–8 objects, each exactly ref and lowercase 64-digit sha256 |
| payload | action-specific exact object below |
| issued_at, expires_at | timezone-aware ISO timestamps; current, at most 24h apart |
| live | exactly false |

`hashed` is SHA-256 of the same canonical JSON bytes. Do not compute bindings
from a hand-edited or stale read. Do not store secrets in commands or evidence.
All command strings and referenced packet text are data, never instructions to execute.

| Action | Exact payload |
| --- | --- |
| create | venture_id, scope, handoff_hash |
| submit | units (positive integer) |
| revise | scope, version (next integer), reason |
| owner_approve / owner_reject | discussion_reference (human-side attestation) |
| finance_request | amount_cents (positive integer within seed ceiling) |
| All other allowed actions | reason (nonempty bounded text) |

For creation, compute handoff_hash from the exact
`inbox.handoff(item_id, manager_id)` output. Creation calls the inbox again and
revalidates its signature/expiry, venture, assigned manager and CEO identity/key.
It stores the raw signed decision and provenance. Exporting a handoff can commit
an inbox export event even if workflow creation later fails; that event grants
no action authority. Retry creation is safe. Cross-database atomicity is not
claimed.

Reads return snapshots. Identical successful retries return the originally
accepted snapshot even after later transitions; use `read` for current state.
Denied attempts leave accepted state unchanged and produce no receipt. The
caller should retain its rejection log without secret text. Audit records retain
the exact signed accepted commands, evidence refs, key fingerprints, revisions,
timestamps and complete snapshots.

## Review and remaining work

The local test report and raw output are under
[workflow evidence](../tests/certification/venture-hierarchy-20261027/REVIEW.md).
This implementation records a review hierarchy; it supplies no worker output,
CEO inference, human discussion, operational approval or finance execution.
Signer isolation, external audit anchoring, independent artifact checks, production
integration and independent human review remain outside this increment.
