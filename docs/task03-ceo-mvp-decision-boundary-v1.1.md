# Task03 signed internal MVP handoff blocker v1.1

Date: 2026-11-01. Base: `ed51f0dc1275b73131fa0a2b819f9f299afc8f11`, main.
Status: safe blocker path implemented for review; autonomous MVP execution remains
unaccepted and disabled in this path.

## Authorization and available records

Authorization source is the Owner's explicit implementation instruction for this
Task03 follow-up: CEO PROCEED_TO_MVP decides, and already-authorized internal MVP
preparation must continue without another mandatory Owner approval. No new scope,
grants, capital, launch, outreach or customer operations may be inferred.
[Task03 v1.0](task03-ceo-mvp-decision-boundary-v1.0.md) and
[Task02 policy](bounded-internal-research-continuation-policy-v1.0.md) remain
historical. This version specifies a new signed denial record and stricter
admission after a disposition; it does not reinterpret old signed transitions.

Read AGENTS.md, both policies, Owner approval policy, Owner idea scope/export
schema, owner admission registry, signed gateway/workflow, preparation broker and
orchestrator, hierarchy runner/daemon, Worker hooks, reservation accounting and
Manager effort policy/tests before changing implementation.

The existing Owner idea decision schema permits APPROVE_FOR_RESEARCH, REJECT or
REQUEST_CHANGES. Its approved assignment scope is INTERNAL_RESEARCH_ONLY.
Gateway admission verifies the full proposal digest and packet binding to this
scope; it does not admit an MVP scope. The preparation-only handoff and CEO
receipt supply no additional development grant. The owner admission registry's
separate build/review scope contract does not establish a verified mapping to a
Task02 research proposal, hierarchy assignment or resource allocation.

The available [Task02 acceptance report](../tests/acceptance-evidence/task02-production-20261101/README.md)
reports three terminal REJECT_OR_DEFER workflows, with Worker counts 4/4/0,
4/4/4 and 4/4/0 across R1–R3. This is historical reported evidence, not freshly
verified current signatures, scope or budget. The current production approval
snapshot and central resource ledger were not available as readable authority
records under the approved project root. Protected evidence directories could
not be read. No privilege escalation, alternate private key source or authority
store outside the root was used.

Consequently, no real current proposal-bound MVP authority was independently
verified. No successful MVP execution transition or hypothetical grant format is
introduced. A synthetic successful MVP grant would invent the missing authority
contract and would not resolve the real blocker.

## Implemented behavior

For a broker-verified OWNER_REVIEW workflow with signed PROCEED_TO_MVP, the CEO
poller uses its existing role signer to checkpoint and submit
`record_mvp_blocker`. The payload must be empty: a caller cannot choose the
blocker, approve execution or supply an allowance. The gateway rechecks current
Owner research approval and complete proposal/packet binding.

The workflow deterministically reconstructs `mvp_handoff` from the signed command
and prior journal snapshot. It includes the full proposal digest, disposition
hash, source snapshot hash, scope hash, research round, BLOCKED status, explicit
`execution_authorized=false` and an actionable instruction to resolve the existing
scope, limits and safe execution path at the broker. No Owner reapproval action
is created. The positive business disposition remains unchanged.

The blocker is a signed journal observation, not a Manager assignment. State,
scope, version, used effort, decomposition, research history and evidence remain
unchanged. No Worker/provider reservation, financial authority or execution
capability is created. The original three-round/four-call-per-round/twelve-call
cumulative limits and complete-digest accounting remain unchanged.

The signed command is checkpointed before dispatch using the existing private
JSON writer. A lost response retries the exact bytes. Changed or expired saved
requests fail closed; no automatic re-signing or paid inference retry occurs.
Fresh broker reads after a commit skip duplicate work. Existing terminal reject
histories receive no blocker and remain untouched.

New journal commands cannot use a completed research disposition to resume,
revise, delegate or approve finance. The runner stops before callbacks, the
daemon stops before session/model/role work, and Worker assignment admission
rejects completed research even if an older signed history ended in a pending
state. Historical reconstruction retains its earlier rules and exact receipts.
The only additional post-disposition work here is the denial record and existing
safe hold/security/termination controls.

The existing Owner progress publisher reports BLOCKED_MVP_HANDOFF with the
actionable blocker through existing status/reason fields, including a conservative
fallback before a blocker is recorded. It preserves the signed positive
disposition, sets no repeat Owner approval requirement and leaves financial
values unavailable. No other repository or website was changed.

## Genuine acceptance still required

A successful internal MVP handoff requires independently verified, current
existing authority that explicitly covers the requested preparation: the complete
proposal/version/scope binding, permitted internal tasks and Manager/Worker
identity, validity and provenance, plus applicable resource ceilings and retained
consumption. That authority must already be consumable through a safe existing
broker path and durable transition. Research budget exhaustion cannot supply
either prerequisite.

Once those records and a compatible path are actually established, evidence must
show a genuine fresh signed CEO decision → bounded Manager assignment → Worker
preparation → signed result/restart/replay, without another mandatory Owner
checkpoint for work already covered. Missing scope or allowance cannot be added
under this instruction. Any genuinely new scope/grant needs separate explicit
authorization outside this change. No capital, launch, outreach, customer
operations or live authority is implied.

The new tests authorize a CEO to record the deterministic blocker and reject
unauthorized roles/signatures/scope changes. They do not claim a successful
authorized MVP execution fixture. Existing research tests exercise the authorized
CEO → Manager → Workers path within its original research scope only.

## Validation and review

Validation results and process records are retained under
`artifacts/task03-mvp-handoff-20261101/` (ignored local artifacts).
All tests use isolated generated signatures, local temporary journals and fake
providers. They are implementation evidence, not real provider or production
acceptance or independent reviewer certification. ADV-001–ADV-049 and /49 remain
unchanged; no ADV certification was run.

- Focused: `infrastructure/python-runtime/.venv/bin/python -B -m unittest
  tests.test_mvp_handoff tests.test_ceo_research_review
  tests.test_research_continuation -v`: 31 tests passed, exit 0 (before the
  final poll integration case).
- Expanded regression: the modules below, 156 tests passed, exit 0, 18.582s.
  This excludes the known failing quota-hold fixture.
- After restricting the display override to OWNER_REVIEW and adding hold display
  coverage: `infrastructure/python-runtime/.venv/bin/python -B -m unittest
  tests.test_mvp_handoff tests.test_ceo_research_review
  tests.test_research_continuation tests.test_owner_research_progress -v`:
  33 tests passed, exit 0, 5.160s.
- Initial broader run including `tests.test_owner_research_quota_hold`: 155 run,
  154 passed, one error: `authoritative research proposal required`. The fixture
  lacks the full digest binding. Loading HEAD's workflow and daemon code into
  memory reproduced the same error (one test, one error, exit 1); this test was
  left unchanged and is not counted as a success.
- `git diff --check`: exit 0. Documentation links resolve. SHA-256 verification
  confirmed all 639 pre-existing readable dirty/untracked files unchanged.
  Inaccessible directories were not inspected. HEAD remains the base commit.

Expanded regression command (with TMPDIR set inside the project artifacts directory):

```sh
infrastructure/python-runtime/.venv/bin/python -B -m unittest \
  tests.test_mvp_handoff tests.test_ceo_research_review \
  tests.test_research_continuation tests.test_worker_inference \
  tests.test_hierarchy_gateway tests.test_hierarchy_runner \
  tests.test_hierarchy_model_callbacks tests.test_hierarchy_multi_worker \
  tests.test_hierarchy_redirection tests.test_venture_workflow \
  tests.test_hierarchy_service_research tests.test_owner_research_progress \
  tests.test_owner_research_admission tests.test_manager_review_budget \
  tests.test_preparation_broker tests.test_hierarchy_bootstrap \
  tests.test_owner_idea_inbox tests.test_owner_research_feedback -v
```

Raw per-test logs and exit files: `regression.log` (initial failure),
`baseline-quota-hold.log`, `final-regression.log` and
`final-focused-control.log` under the artifact directory above.
`verification.json` records preservation and reference checks.
All bridge-started test processes were polled to exited before their completed
project-local logs were read. Bridge process IDs/PIDs:
`proc_mvy6c1ei_d9chwm`/2395137 (initial focus),
`proc_mvy6ctbt_1ha2bg`/2395515 (initial regression),
`proc_mvy6e07i_yh05f5`/2400400 (31-test focus),
`proc_mvy6e0u1_v8q0ds`/2400429 (HEAD baseline),
`proc_mvy6fbdx_gkj7jc`/2409550 (156-test regression),
`proc_mvy6hhyl_gll4s8`/2419093 (33-test final focus).
Each start returned its bridge log path; test output was redirected into the
project-local logs to respect the project-root boundary.


Changed implementation files:
agents/ceo/venture_workflow.py, hierarchy_gateway.py, hierarchy_research_daemon.py,
hierarchy_runner.py, preparation_broker.py, scripts/publish_owner_research_status.py.
Added tests/test_mvp_handoff.py and this versioned document. Original dirty files
are outside this change.

No commit, push, deployment, service restart, real CEO attachment, external action,
capital action, grant creation or production authority mutation was performed.
