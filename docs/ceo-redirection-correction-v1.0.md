# Bounded CEO redirection correction v1.0

2026-10-31. Local implementation against main `5efaf94`; no activation,
commit, deployment or paid inference authorized by this note.

The existing signed journal already permits CEO `revise` from
CEO_REDIRECTION, requires version + 1, retains consumed effort, clears
decomposition and approvals, and returns to MANAGER_PENDING. Its general
revision API can change scope; this adapter deliberately permits less:
one automatic correction from version 1, immediately after the assigned
Manager's signed reject_premise, with remaining effort. Every scope field
(tasks, actors, budget, seed ceiling and preparation mode) must be identical.
A repeated rejection at version 2 stops before another CEO callback, including
after restart. Holds, security clearance, owner rejection and exhaustion
receive no automatic revision. The journal's existing 100-revision bound
and all inference quotas remain unchanged.

CEO reasoning uses the existing metered provider and durable call checkpoint.
Digest-verified Manager evidence must bind the rejection command's revision,
previous snapshot, scope and reason before inference. The CEO supplies the
reasoned correction as immutable preparation evidence; local trusted code
constructs the original scope and next version, and the original pinned CEO
signer signs the bound command. No deterministic CEO decision replaces that
review. Invalid responses fail closed; ambiguous provider attempts cannot
retry automatically. The Manager receives the CEO correction evidence and
must propose decomposition again; CEO decomposition approval and every
subsequent review, including human owner approval, remain required.

The decomposition prompt now describes exact scoped A/B tasks and C's
dependency on both, replacing unrelated demand/competition/feasibility labels.
This removes an observed prompt contradiction; successful real model
redecomposition is not established by synthetic tests.

Runner, service, callback, existing provider state check and existing broker
gateway are the only implementation paths changed. Gateway revisions are
restricted to the same bound and preserve authenticated historical exact replay.
No new service, table, workflow ID, allowance, key or ledger reset is introduced.
The runtime workflow and CEO service were not accessed or changed.

Validation uses local temporary signed journals, fixture keys, mock providers
and existing regression suites. It establishes local behavior only, not
deployed two-VM behavior, model judgement or available runtime quota.
Executed results: baseline 49 tests passed; expanded regression 202 tests
passed; final focused verification after replay/payload checks 20 tests passed.
Each completed log reports exit code 0. `git diff --check` passed.
Raw command/results are retained in ignored `artifacts/ceo-redirection-*.log`.
No real CEO, capital/payment, launch or deployment was used.
ADV-001–ADV-049 and /49 remain unchanged.
