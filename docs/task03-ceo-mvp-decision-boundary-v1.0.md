# Task03 CEO MVP decision boundary correction v1.0

Date: 2026-11-01. Base HEAD: `14f51b27f4ff658b4705674152636e070e5d8b56`.
Authority source: Owner's explicit Task03 correction instruction in this session.

The CEO may decide PROCEED_TO_MVP and continue already-authorized internal MVP
work without a new Owner checkpoint. Owner approval remains required for
out-of-scope capital, launch, customers and external work. This narrowly supersedes
the wording in [Task02 policy v1.0](bounded-internal-research-continuation-policy-v1.0.md)
that treats every positive MVP disposition as requiring separately authorized
development. It supplies no proposal-specific execution grant or new authority.
Historical policy, signed decisions and prior acceptance reports remain unchanged.

A signed MVP disposition records the CEO's decision. Actual MVP execution still
requires explicit current scope, applicable resource limits and an existing safe
execution path. Research reservations are not MVP permission; their exhaustion
cannot create an MVP allowance, reset a proposal's quotas or imply business failure.

The prompt and new-response validator now distinguish PROCEED_TO_MVP's
`Internal MVP:` next task from the earlier READY_FOR_OWNER_DISCUSSION's
`Owner proposal:`. The positive disposition may report an execution blocker while
remaining positive. Attribution, customer/problem/validation criteria, unknowns,
round limits and historical completed-record reuse remain enforced. The text
validator checks response shape and selected prohibited task wording; it cannot
authenticate an execution grant or replace the broker's authority checks.

## Existing-path finding and blocker

Inspected AGENTS.md, Task02 policy, CEO review/validator, signed workflow creation,
transition reconstruction, research daemon, hierarchy gateway/service/runner,
preparation broker/orchestrator, Worker inference accounting and related tests.

- `HierarchyGateway._research_entry` requires APPROVE_FOR_RESEARCH and
  INTERNAL_RESEARCH_ONLY. Bootstrap binds the exact research instructions to the
  signed CEO receipt and handoff; `research_authority` rechecks that binding.
- `VentureWorkflow._research_transition` persists a positive research disposition
  in OWNER_REVIEW. Its verifier reconstructs that same state on restart. Changing
  this existing transition would reinterpret historical signed snapshots.
- The daemon skips workflows with a recorded disposition. Manager entry points
  accept preparation/decomposition/review states; OWNER_REVIEW has no existing
  internal MVP handoff. The gateway's automatic revision permits only the existing
  bounded same-scope correction, not a change from research to development.
- Worker inference requires a signed ready assignment and centrally reserved
  capacity. Task02 allows at most four Worker calls per research round and twelve
  cumulatively per approved proposal. No MVP-specific execution scope or allowance
  was established in the inspected project path.

Therefore no state-machine change or execution transition was implemented. The
blocker is the absence of a verified proposal-bound MVP execution scope and safe
existing transition, not a requirement to repeat Owner approval for work already
authorized. Relabeling OWNER_REVIEW or resetting research effort would not supply
either missing prerequisite.

The existing [Task02 acceptance record](../tests/acceptance-evidence/task02-production-20261101/README.md)
reports three signed terminal REJECT_OR_DEFER decisions. That is prior recorded
evidence, not a fresh independent verification of production signatures here.
No production authority store outside the approved project root was inspected.
No signed history, approval, quota, runtime configuration or deployed file changed.

## Validation and review status

Focused: `infrastructure/python-runtime/.venv/bin/python -m unittest tests.test_ceo_research_review tests.test_research_continuation -v`
— 23 tests passed. These include isolated generated signed CEO MVP responses,
unchanged terminal-state reconstruction after restart, denied delegation/revision,
denied disposition replacement, denied fourth round and denied Worker reservation.

Regression: the focused modules plus `test_worker_inference`,
`test_hierarchy_gateway`, `test_hierarchy_runner`, `test_hierarchy_model_callbacks`,
`test_hierarchy_multi_worker`, `test_hierarchy_redirection`, `test_venture_workflow`,
`test_hierarchy_service_research`, `test_owner_research_progress` and
`test_owner_research_quota_hold` — 113 run, 112 passed, one error. The quota-hold
fixture omits the authoritative research proposal binding and raises
`ValueError: authoritative research proposal required`. Re-running that fixture with
HEAD's CEO review module loaded in memory reproduced the same error (one test,
one error). It is not counted as PASS. `git diff --check` and documentation-link
checks passed. SHA-256 comparison confirmed all 639 pre-existing readable
modified/untracked files unchanged; inaccessible directories were not inspected.

Raw commands/process IDs, logs, exit files and preservation hashes are under
ignored `artifacts/task03-mvp-boundary-review-20261101/`. This is local isolated
test evidence, not production execution or independent acceptance. ADV-001–049
and the /49 denominator are unchanged; no ADV certification was run.

Status: prompt/validator correction implemented for review. Autonomous internal
MVP continuation remains blocked in this path. No commit, push, deployment, real
CEO attachment, external action or capital action was performed.
