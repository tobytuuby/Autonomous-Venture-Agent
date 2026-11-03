# Task03 existing authority inspection v1.2

Date: 2026-11-01 UTC. Inspected checkout: `c8fab3674b434a1fce2b54428b7e3a0de66911cc`, branch `main`.
This is an evidence supplement to [v1.1](task03-ceo-mvp-decision-boundary-v1.1.md);
it changes no policy, authority contract, signed history or limits.

## Decision and exact blocker

No current proposal-bound internal MVP authority could be independently verified
inside the approved project root. Consequently no executable MVP transition is
authorized by the evidence available here. The existing signed `record_mvp_blocker`
path remains the safe response to a verified positive disposition; this inspection
did not submit a production command or infer a fresh positive production decision.

There are two distinct blockers:

1. Current production authority and consumption cannot be inspected from this
   root. Expected project-local `artifacts/preparation-authority/` and its
   `authority.json`, `owner-research-feedback.json`, `resources.sqlite` and
   `hierarchy/workflow.sqlite` all returned FileNotFoundError. A bounded
   filename inventory of artifacts, acceptance evidence and infrastructure found
   no readable current feedback snapshot, resource ledger, reviews database,
   hierarchy config or workflow journal. Protected evidence directories returned
   permission denied and were not bypassed.
2. The existing CTKFamily approval contract establishes research authority only.
   Neither that contract nor the admission registry supplies an existing verified
   mapping from these research proposals to MVP tasks, Manager/Workers and retained
   resource consumption. A CEO positive disposition supplies no missing grant.

Repository service definitions describe installations outside this root:
`venture-owner-api.service` references review/discovery databases beneath
`/var/lib/venture-review/inbox`; the CEO service references a hierarchy config
beneath `/usr/local/lib/venture-ceo-level2c`; the broker mTLS service references
`/etc/venture-control/broker-mtls.env`. These are checked-in configuration evidence,
not a fresh observation of installed production settings. Those paths, environment
files, credentials and private keys were not accessed. No claim is made about
current signatures, revocation, remaining daily capacity or production reachability.

The readable `infrastructure/venture-ceo-kernel-gate.runtime.json` is an ADV gate
report, not an authority grant. The readable active-worker policy specifies four
requests and 1,024 output tokens; the separate dirty worker-policy file specifies
four and 512. Neither file establishes which policy production currently consumes.
Neither was modified, and neither is a proposal-bound MVP allowance.

## Exact existing CTKFamily authority and safe use

The repository's audit copy of `pages/venture_ideas.php` uses existing login plus
separate timed Owner verification and CSRF protection, then calls
`POST /v1/owner/reviews` with `X-Owner-Intent: explicit`. It accepts exactly
`cycle_id`, `proposal_digest`, `decision` and `reason`. Its allowed decisions
are `APPROVE_FOR_RESEARCH`, `REJECT` and `REQUEST_CHANGES`. This historical
audit copy does not prove the current remote website implementation.

The local matching contract is:

- `OwnerIdeaInbox.review` binds a human decision to a known discovery cycle and
  the complete proposal SHA-256, stores it once in `owner_idea_reviews`, and
  rejects replacement of an existing review. It returns
  `venture_admitted=false` and `capital_allocated=false`.
- `publish_owner_idea_feedback.export` joins that exact proposal to its decision
  and emits `INTERNAL_RESEARCH_ONLY`, `APPROVED_NOT_ASSIGNED`, with
  `advisory_only=true`, `venture_admission=false` and
  `financial_authority=false`. Free-text reasons cannot change this scope.
- The existing `/v1/hierarchy/bootstrap/prepare` and
  `/v1/hierarchy/bootstrap/commit` route verifies that snapshot, proposal digest,
  CEO signature and exact packet/instructions binding before admitting research.
  CEO directs Manager, Manager proposes decomposition, CEO approves, Workers
  return evidence through Manager. Existing reservation checks retain consumption
  under the full proposal digest: three rounds, four Worker calls per round,
  twelve cumulatively; no new workflow ID renews it.
- A completed positive disposition uses the existing signed blocker, preserving
  the positive decision without a repeat Owner approval requirement. A terminal
  reject cannot be restarted as MVP work. The separate
  `VentureAdmissionRegistry` recognizes signed build/review scopes, but its local
  eligibility evidence grants no execution and is not mapped to this hierarchy.

Safe use is therefore to consume an existing verifiable research approval through
that existing route within its remaining original bounds. Do not resubmit an
already-reviewed idea, reinterpret its reason as an MVP grant, create a new workflow
to renew quota, mutate old approvals, or widen the CTKFamily decision schema here.
The historical Task02 report lists three terminal REJECT_OR_DEFER workflows and
48 central reservations at its observation time; those numbers are historical
reported evidence, not current independently verified ledger balances.

Resolving the access blocker means making the existing non-secret, operator-owned
authority evidence and retained ledger consumption verifiable within the allowed
root through an approved mechanism. If that evidence already explicitly covers
internal MVP preparation, use it without another mandatory Owner checkpoint.
If it does not, this instruction authorizes neither fabricating such consent nor
creating a new scope/allowance. No runnable MVP path can be honestly supplied here.

## Scoped changes and evidence

Added `tests/test_task03_existing_owner_authority.py` with four integration and
denial tests. They exercise existing Owner review -> exporter -> signed gateway
handoff, exact proposal/scope binding, immutable reviews, unsupported MVP decisions,
and missing current snapshots. One test includes MVP wording in the review reason
and proves that the export and handoff remain research-only. Existing implementation
needed no change to enforce these denials. Generated test keys and isolated
temporary databases are test inputs, not human consent or production evidence.

Validation results and raw per-test logs are retained under
`artifacts/task03-authority-inspection-20261101/`. Temporary files are confined
there or to the project-local fixture roots. Commands use
`infrastructure/python-runtime/.venv/bin/python -B -m unittest` with project-local
TMPDIR. Focused and regression results follow.

No commit, push, deployment, service restart, real CEO attachment, provider call,
capital action, customer action, signed approval mutation or quota reset occurred.
Task03 production end-to-end acceptance remains OPEN. ADV-001–ADV-049 and /49
remain unchanged; no ADV certification or independent reviewer acceptance is claimed.

## Validation results and review decision

- Focused: 21 tests passed, exit 0, 5.942s. Modules:
  tests.test_task03_existing_owner_authority, tests.test_mvp_handoff,
  tests.test_owner_research_admission, tests.test_owner_api.
- Expanded regression: 168 tests run, 167 passed, one error, exit 1, 21.475s.
  The existing tests.test_owner_research_quota_hold fixture raises
  ValueError: authoritative research proposal required. This same limitation was
  recorded in Task03 v1.1. An isolated run of that unchanged module reproduced
  one test / one error, exit 1, 0.028s, without loading the new test module.
  No full-suite PASS is claimed; the unrelated failing fixture remains unchanged.
- Initial focused run: 21 tests, one error because the new fixture's receipt used
  its old reviewed_utc rather than the actual exported timestamp. Corrected the
  test to sign the exact exported packet; the final focused and expanded runs
  both pass all four new tests. The initial raw failure remains in focused.log.
- git diff --check: exit 0. HEAD remains the inspected commit. The dirty worktree
  remains dirty; no existing implementation file was edited by this task.
- SHA-256 comparisons preserved all 34 individually enumerated baseline dirty
  text files. This is a bounded preservation check, not a claim to have inspected
  inaccessible directories or every file under collapsed untracked directories.

Exact test commands and bridge PID/log metadata are in local processes.json;
raw scenario output is in focused-final.log, regression.log and
quota-hold-isolated.log, with adjacent exit files. Every process was polled to
exited before its completed project-local log was read. Bridge log paths were
recorded as metadata only; no out-of-root log contents were accessed.
The original failed focus process was proc_mvy8nmcf_e5fy6w / PID 2474243;
its bridge log path was
/home/epsilon/.chatgpt2localbridge/process-logs/proc_mvy8nmcf_e5fy6w.log.

- proc_mvy8ocr5_a0p7el / PID 2477480 / exited

- proc_mvy8ojh1_pquwld / PID 2477581 / exited

- proc_mvy8q2qq_ma8ocg / PID 2484038 / exited

Evidence classification: repository contract inspection and local isolated
implementation tests. Production records, signatures, configured quota and
runtime MVP dispatch remain unverified. Operator impact is limited to two new
review files plus ignored local evidence; there is no new operational authority.
Review decision: retain the existing blocker and keep genuine Task03 MVP
acceptance open until existing authority and consumption can be verified. No
external review or production acceptance is represented by this decision.
