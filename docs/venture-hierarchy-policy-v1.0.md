# Venture hierarchy review policy v1.0

2026-10-27. Owner-requested, local preparation increment from main `8b85728`.
Governing boundary: [owner venture approval v1.0](owner-venture-approval-policy-v1.0.md)
and [finance control v1.2](venture-finance-control-and-transaction-visibility-v1.2-DRAFT.md).
This supplements the [core synthetic plan v1.1](core-synthetic-orchestration-plan-v1.1.md);
it does not change a numbered phase, phase acceptance, ADV universe or live authority.

## Authority and purpose

The hierarchy records CEO → manager → worker → manager review, including improvement,
premise rejection, CEO final recommendation, human owner review, and a CEO finance
authorization **request**. It never creates agents, runs tasks, releases money,
allocates funds, submits a provider request or grants operational authority.
Before owner approval, every task is proposal preparation only. A signed manager
delegation is a preparation record, not operational manager execution.

Every event needs an explicit actor ID and role authenticated by a separately
pinned Ed25519 public key. CEO and owner roles have at most one configured actor
each; all actor keys must be distinct. Manager and worker must match the assigned
IDs in the exact scope. A role string, model response, inbox acknowledgement or
advisory review cannot substitute for a verified signature. Missing keys deny.
No private keys, signer, key enrollment or provider inference exist here.

Owner commands require the independently pinned owner key and
`origin=human_out_of_band`; a CEO key cannot sign for the owner. The trusted
owner-side process must authenticate Kalaap Das, conduct the discussion and
attest the decision outside the model channel. Labeling model text “human”
does not authenticate it. A signature establishes signer attestation, not
independent proof of a human conversation.

## Allowed transitions

Creation consumes a verified inbox handoff and begins MANAGER_PENDING.

| State | Action / role | Next state |
| --- | --- | --- |
| MANAGER_PENDING | delegate / manager | WORKER_PENDING |
| MANAGER_PENDING or MANAGER_REVIEW | reject_premise / manager | CEO_REDIRECTION |
| WORKER_PENDING | submit / assigned worker | MANAGER_REVIEW, or BUDGET_EXHAUSTED |
| MANAGER_REVIEW | improve / manager | WORKER_PENDING |
| MANAGER_REVIEW | manager_approve / manager | CEO_REVIEW |
| CEO_REVIEW | ceo_approve / CEO | OWNER_REVIEW |
| CEO_REVIEW | redirect / CEO | CEO_REDIRECTION |
| OWNER_REVIEW | owner_approve / human owner | OWNER_APPROVED |
| OWNER_REVIEW | owner_reject / human owner | OWNER_REJECTED |
| OWNER_APPROVED | finance_request / CEO | FINANCE_REQUESTED |
| CEO_REDIRECTION, OWNER_REJECTED, BUDGET_EXHAUSTED | revise / CEO, next version | MANAGER_PENDING |
| HOLD | resume / CEO | CEO_REDIRECTION |
| SECURITY_HOLD | clear_security / human owner | CEO_REDIRECTION |
| Any nonterminated state | terminate / CEO or owner | TERMINATED |

CEO, manager or owner may hold; ordinary hold cannot downgrade SECURITY_HOLD or
FINANCE_REQUESTED. Any assigned participant or pinned security actor may raise a
security hold. Holds, security holds, redirection and termination invalidate the
current owner receipt and local finance request. Security clearance and ordinary
resume both return to redirection, requiring a new version and all reviews.
TERMINATED accepts no new transition. A historical identical retry is only a
historical receipt, never a new action or proof of current eligibility.

Owner rejection cannot be replaced in place or advanced directly to finance.
Correction requires a CEO revision, the next version, manager/worker review,
CEO review and fresh human owner review. No gate can be skipped.

## Scope, evidence and budget

The signed scope fixes PREPARATION_ONLY mode, manager, worker, 1–8 explicit task
descriptions, an integer preparation effort ceiling of 1–10,000 units, and an
integer hypothetical seed request ceiling of 1–10,000 cents. Units are a local
review-work counter, not dollars or measured provider usage. Every worker
submission declares positive integer units. Over-budget submissions are recorded
as BUDGET_EXHAUSTED and cannot advance to approval; the attempted units remain in
the signed command, while accepted consumption stays unchanged. Delegation at
zero remaining units also records exhaustion. Corrections retain consumption;
any ceiling/task/actor change requires an explicit new scope and version.
The seed ceiling creates no available balance and does not reserve portfolio funds.

All commands bind workflow ID, current revision, prior complete snapshot hash,
proposal version and scope hash. Owner approval consequently binds the accumulated
proposal, task scope, budget, immutable evidence map and all preceding reviews.
CEO finance requests reverify the current owner signature, origin and validity
window and cannot exceed the exact seed ceiling. All finance output says
REQUEST_ONLY; execution and money release remain false.

Evidence references have bounded names and SHA-256 digests; the same name cannot
be rebound to different bytes, even across revisions. No URI is fetched or
executed. These are signer-supplied content bindings; the software does not
independently verify the underlying artifacts or the truth of a review.

This workflow's owner receipt is a review/request receipt, **not**
`VentureAdmissionRegistry` operational approval. Any future operational executor
must separately consume the canonical signed owner-admission gate and independent
finance/broker/live checks atomically. No existing approval registry is changed
or bypassed. Studio Restock Kit remains an unapproved pilot.

## Durability and limits

Separate private SQLite state inside the approved project root reuses the inbox
storage primitive: FULL synchronization, BEGIN IMMEDIATE, atomic event/snapshot
commit and rollback. Every read/mutation verifies event hashes, sequence, prior
hashes, signed command lineage and snapshot consistency. Signatures are checked
against current trusted pins; changing/removing a pin can block historical reads
and requires a controlled migration, not agent key replacement.

A globally unique request ID replays an identical accepted command without a new
event; changed use of the ID is denied. Rejected commands commit nothing and can
be corrected and retried. Exact successful replay returns the original snapshot,
which may be historical; read current state separately. Receipt validity is
rechecked on replay. Creation also rechecks the inbox handoff at retry time.
No rejected gate mutates accepted state or enables a later gate.

Bounds: 1,000 workflows, 5,000 total events, 100 revisions per workflow,
256 immutable reference names, eight evidence refs per command and 16 KiB commands.
Capacity failure closes the transaction.

The journal is local tamper evidence, not a privileged attacker boundary.
A fully rewritten last event/snapshot or restored complete database, malicious
trusted control plane, compromised signer or filesystem race needs isolation,
secure backups and external audit anchoring. Receipt expiry is enforced; a remote
revocation service and external artifact verification are not implemented.
There is no real CEO attachment, scheduler/service wiring, customer contact,
payment, public deployment or systemd change. ADV-001–ADV-049 and /49 are unchanged.
