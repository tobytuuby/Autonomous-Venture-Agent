# Level2D Manager review budget correction v1.0

2026-10-31. Implementation correction for bounded PREPARATION_ONLY review.
This adds no operational authority, approval layer, provider allowance or service.

## Decision contract

Remaining effort is the signed scope budget minus durable used units. At zero
remaining effort, Manager review permits only manager_approve or hold.
Manager may approve sufficient documentation for CEO_REVIEW; this attests
preparation sufficiency, not executed tests or verified runtime behavior.
Paper-only cases, procedures and acceptance criteria must be assessed against
the scoped preparation tasks. Pending runtime tests alone do not establish
missing preparation. Substantively deficient preparation must hold with a reason
that explicitly identifies exhaustion and the missing work.

With remaining effort, the existing improve route remains available. Multiworker
improvement still discards the old decomposition and requires a fresh proposal,
CEO decomposition approval and new individual Worker evidence. No gate is skipped.

## Signed enforcement and historical compatibility

New signed improve, delegate, propose_decomposition and revise commands are
rejected once used units reach the existing ceiling. This applies in the journal
even when callers bypass the callback or gateway. Neither an increased scope
budget in a revision nor a hold/resume sequence can restart an exhausted cycle.

The existing hierarchy runner constrains callback actions before signing. The
existing broker permits the assigned Manager's hold only for an exhausted
MANAGER_REVIEW or MANAGER_PENDING snapshot. Existing signatures, actor binding,
stale snapshot checks, evidence integrity and broker Worker assignment checks
remain authoritative.

Historical reconstruction deliberately retains the previous signed transition
rules. Changing them retroactively would invalidate already committed journals.
Exact authenticated retries return their historical receipts without appending
events; the authoritative current snapshot still governs subsequent work.
No historical receipt supplies a new assignment, allocation or reservation.

The reported level2d-multiworker-remediation-1 ledger remains BUDGET_EXHAUSTED at
revision 11: Manager improve at revision 9 followed consumption of all five
effort units, re-decomposition at revision 10, then budget denial on CEO
decomposition approval. This correction does not rewrite, resume or allocate
anything to that workflow. Its protected live journal was not opened during
this implementation; the stated sequence is owner-supplied context, not a newly
independently verified live observation.

## Evidence and review limits

tests/test_manager_review_budget.py uses ephemeral signing keys, local durable
artifacts, fake inference and the existing gateway. It covers sufficient and
deficient zero-budget work, direct signed bypass attempts, nonzero improvement,
single-worker enforcement, historical reconstruction, exhausted historical
pending records, restart and replay, and restricted broker hold access.
The existing workflow exhaustion regression is updated to reject a new cycle.

Validation used infrastructure/python-runtime/.venv/bin/python -B -m unittest
with TMPDIR set to the project artifacts directory.

- Focused modules: test_manager_review_budget, test_hierarchy_model_callbacks,
  test_hierarchy_multi_worker, test_hierarchy_gateway, test_hierarchy_runner,
  test_venture_workflow: 53 tests, OK, exit 0 (8.107 seconds).
- Final test_manager_review_budget after two added security cases: 8 tests,
  OK, exit 0 (1.429 seconds).
- Broader modules: test_hierarchy_redirection, test_hierarchy_providers,
  test_hierarchy_bootstrap, test_hierarchy_artifact_store, test_worker_inference,
  test_preparation_broker, test_preparation_exchange, test_level2c_central_roles,
  test_level2d_worker_provision, test_level2d_worker_renewal,
  test_broker_mtls_entrypoint, test_broker_isolated_mtls,
  test_authenticated_handoff, test_owner_approval, test_control_plane,
  test_compute: 225 tests, OK, exit 0 (64.956 seconds).
- git diff --check: exit 0. All 633 files in the initial dirty/untracked
  baseline retained their SHA-256 hashes. HEAD remained
  7005a7087691fb8bd52e3a050a2ea79ba8d42905.

The first focused run had 52 successes and one error: an older exhaustion test
expected improve at zero effort and subsequent reactivation. That expectation
was corrected to assert rejection, hold and no restart. Its raw output remains
in artifacts/manager-budget-focused.log.

Raw final output is retained in artifacts/manager-budget-focused-final.log,
artifacts/manager-budget-final-cases.log and artifacts/manager-budget-regression.log.
These files contain individual test results and exit status.
These are local regression results, not real-provider acceptance or independent
reviewer certification. No claim is made about real-model review quality.
ADV-001 through ADV-049 and the /49 denominator are unchanged.
No deployment, commit, push, real CEO attachment, capital action or real
provider inference is part of this correction.
