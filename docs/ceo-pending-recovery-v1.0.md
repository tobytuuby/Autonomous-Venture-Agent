# CEO pending recovery implementation and remediation v1.0

Date: 2026-11-02. Base: 8e999120254d2e8ad859ce9ae0bfc5dfb1b9fc9d.
Scope: pending internal research CEO reviews only. This implements the owner's
narrow blocker request; it grants no deployment, operational, capital or launch
authority and changes no signed history, research rounds, quotas or ADV denominator.

## Recovery decision

The existing local calls row binds canonical request, snapshot-derived identity
and attempt. PENDING checkpoint request hash, current signed snapshot, exact current
or allowlisted historical prompt, actor, session and policy must still match.

An accepted local response follows the existing read-only replay path. Its original
bytes, historical prompt compatibility and immutable provider-intent capture remain
unchanged.

For a NULL local response, the Control-local caller uses reserve_exchange and
execute_reserved against the existing private resources.sqlite ledger. It never
creates a replacement call identity or attempt. A new optional CEO-only reservation
binding, execution_mode=CONTROL_LEDGER_V1, distinguishes the tracked executor from
historical direct execution. The HTTP execute endpoint continues to select Manager
role; request JSON cannot grant CEO execution.

The broker reservation method atomically checks the existing call key:
- No original reservation in an existing established session: original execution
  was impossible because the old path required committed reservation before provider
  access. The same intent can reserve its first slot under current authority/caps.
  The atomic unique key prevents a concurrent old reservation from also succeeding.
- Exact mode-bound reservation: reuse its charged slot. Missing remote_executions
  row proves NOT_STARTED because this mode always checkpoints before provider I/O.
- Exact COMPLETE execution: retrieve its stored response without configuring or
  calling the model, then checkpoint locally and apply existing review validation.
- PENDING execution: explicit PROVIDER_EXECUTION_AMBIGUOUS, with no paid retry.
- Legacy reservation without the mode binding, changed binding, missing ledger or
  missing session: CEO_RESERVATION_PROOF_REQUIRED. Absence in a lost/recreated ledger
  is not proof. Existing legacy reservations are never upgraded in place.

The established config context is retained, including approved legacy session rounds;
review code no longer replaces that binding with the observed research round count.
The authoritative session and policy comparison still owns acceptance. Revocation,
epoch, exact policy, shared session ceiling and daily ceilings remain enforced.
A proven NOT_STARTED execution is its original first execution, not a retry of a
possibly paid request. Failed/ambiguous reservations are never refunded.

## Live remediation requirements (not performed)

Reported incident: Client Document Checklist, research-5900c3db9bb5bd74601e3f9d,
CEO_REVIEW revision 9, PENDING checkpoint SHA prefix 89ea3a, created
2026-11-02T21:50:26. These are owner-supplied observations, not independently verified
runtime evidence. The full checkpoint/snapshot hashes and broker state were not read.

An authorized operator must:
1. Preserve the original PENDING checkpoint, local calls row/request/attempt and
   broker ledger with audit provenance. Verify the full snapshot hash and signed
   lineage against revision 9, the request hash, original session, proposal/scope,
   provider endpoint/model, active policy and authorization.
2. Under separately authorized rollout, update the existing Control broker
   reservation code and existing CEO research process together; no new service is
   needed. Retain the existing ledger and state paths. Restart the existing poller
   to clear its in-memory blocked snapshot after evidence/configuration is checked.
   The local executor requires existing private Control authority/ledger access
   satisfying the current UID/mode checks. If unavailable, remain blocked; do not
   broaden ledger permissions or run a new service to bypass the boundary.
3. If the established session is intact and the original reservation is absent,
   the updated atomic broker method can prove the original request never executed,
   reserve exactly that identity/attempt within caps, and execute it once.
4. If an exact tracked COMPLETE response or accepted local response exists, replay
   it. If a legacy reservation exists with NULL local response, or an execution is
   PENDING, keep the workflow blocked. Missing traces, elapsed time, no visible
   response or a provider error do not prove nonexecution.
5. A legacy executed response requires independently correlated original provider
   response evidence and an explicitly authorized reconciliation mechanism; this
   patch does not invent a provider retrieval API, import evidence, relabel the
   legacy reservation, or authorize manual ledger/checkpoint edits. Legacy ambiguous
   cases cannot safely be unblocked by deploying this patch alone.

Do not delete PENDING, reset research, alter signed history, replace session IDs,
change attempts, replenish caps or create a fresh paid call to resolve ambiguity.

## Validation and assessment

Final clean-copy validation overlays only the five changed implementation files and
new test file onto git archive of the base commit inside approved project artifacts.
Command and full per-test raw report are in
tests/acceptance-evidence/ceo-pending-recovery-20261102/.
Result: 107 tests, OK, exit 0. Focused final suite: 13 tests, OK, exit 0.
Earlier incremental runs: 75 tests and 104 tests, both OK, exit 0.
git diff --check passed.

Tests cover original reserved intent/attempt, absence proof, exact response replay,
ambiguous block, legacy refusal, changed identity/attempt/context/policy, revocation,
missing ledger/session, exhausted caps, Manager endpoint denial, future venture
restart, checkpoint integrity, accepted response replay and historical prompts.
All provider calls are fake and all ledgers are isolated temporary fixtures.

Evidence classification: implemented and isolated execution verified from raw logs.
Not deployed, not runtime verified, not independently verified provider execution.
No live ledgers were accessed. No real CEO was attached or enabled; no real provider,
capital, payment, launch, deployment or customer operation was performed.
ADV-001 through ADV-049 and /49 remain unchanged; these tests are supplemental.

Review decision: suitable for source commit after focused and clean-copy checks.
Production remediation remains conditional on actual preserved broker evidence and
separate rollout authority. Existing unrelated dirty-worktree changes are preserved
and excluded from the commit. Residual risks are unavailable/corrupt authority
history, inaccessible Control ledger and legacy untracked provider execution; each
must remain an explicit block rather than inferred success.
