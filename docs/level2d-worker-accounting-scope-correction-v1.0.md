# Level2D Worker accounting scope correction v1.0

Date: 2026-10-31. Status: source correction for owner review; no commit,
deployment or paid verification authorized by this note.

This records the owner's bounded instruction to restore the original Worker
request scope. Commit 2c66b35 counted a maximum of four calls per workflow;
0b94a7a retained that shared workflow ceiling while introducing signed
multiworker assignment checks and a four-call assignment ceiling. Commit
b7c43e2 broadened accounting to all workflows for a venture and carried their
historical policy minima across those workflows.

This correction supersedes only the venture-wide accounting and consequent
budget-exhaustion interpretation in
[level2d-multiworker-remediation-v1.1.md](level2d-multiworker-remediation-v1.1.md)
and [v1.2](level2d-multiworker-remediation-v1.2.md). Their historical observations
remain evidence of the behavior inspected at that time. A distinct signed
workflow does not require raising a cumulative venture ceiling to obtain its
own bounded allowance. This does not grant permission to create or run one.

The accounting unit is the CEO-signed workflow verified by the existing
hierarchy journal and assignment authorization. Each workflow permits at most
min(current policy maximum_requests, every retained per-workflow historical
policy maximum_requests), always at most four; each assignment also remains
limited to four. Actors and assignments share the workflow allowance.
Changing identity, attempt, actor, assignment, policy, epoch, UTC day or service
process cannot reset that workflow's retained charges. Historical minima mean
ceilings recorded in retained reservation policies; an unrecorded policy
configuration interval is not independently reconstructible from this ledger.

Legacy single-worker reservations without assignment IDs count toward their
exact workflow, including retired actors and incomplete/failed calls. Relevant
historical rows with absent or invalid integer request ceilings fail closed.
Rows that cannot identify a workflow also fail closed because their scope is
unknown. A known different workflow needs no current journal lookup or policy
reauthorization to exclude it from this workflow's accounting. These checks
verify accounting fields in the trusted Control ledger; reservation rows are
not independently signed authorization proofs. Current authorization still
verifies the signed journal before reservation or execution. No reservation is
deleted, refunded, migrated or replayed; exact duplicate behavior is retained.

The independent [central daily quota](level2c-central-reservation-phase1-v1.0.md)
still charges each new Worker reservation atomically in the same transaction,
alongside other roles using that ledger. Its request/token maxima, owner and
capital checks, policy JSON, inference execution checks and all other maxima
are unchanged. Callers cannot supply a venture ID or accounting override.
Exhausted workflows remain exhausted.

Residual risk: separately authorized distinct workflows each have their own
allowance. Repeated workflow creation can increase aggregate consumption,
subject to the shared daily request/output-token quota and existing authority
gates. This is not a venture-lifetime or aggregate monetary cap. Reserved
output tokens and request counts do not establish actual provider usage,
pricing or spending. Workflow proliferation controls or a currency budget
would require separate policy and implementation review.

Validation is local synthetic evidence only, using temporary fixture journals,
keys, ledgers and fake providers. It does not establish deployed behavior or
independent acceptance of a real Level2D journey. No real CEO, signed runtime
ledger/key, paid inference, capital/payment, launch or deployment is used.
ADV-001–ADV-049 and the /49 denominator remain unchanged.
