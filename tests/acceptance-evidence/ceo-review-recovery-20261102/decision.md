# Durable CEO research review recovery — 2026-11-02

Base: ed52957d71e9cc9c0332a46759f2f9e80bc23c36, main.

The existing review rejected all non-COMPLETE checkpoints before inspecting the
completed metered response. The correction reconstructs the existing request
from the current workflow and digest-verified artifacts, and checks the exact
PENDING snapshot/request hash, current broker snapshot, CEO policy model/actor,
canonical saved request, call identity and durable attempt. Only the canonical
scoped research-review-inference.sqlite is opened, in SQLite read-only mode.
No HierarchyProvider or configured model is constructed during recovery.
Missing, ambiguous, changed or malformed evidence fails closed.

A recovered response goes through the same strict JSON and recommendation
validator as a new response before the existing signing and atomic completion
path. An invalid response retains its original PENDING checkpoint and unchanged
ledger and surfaces the validator error. Historical COMPLETE packets retain
existing behavior. No paid retry, reservation, quota reset, ledger mutation,
intent deletion, response rewriting or new execution authority is introduced.

Implementation: agents/ceo/ceo_research_review.py.
Tests: tests/test_ceo_research_review.py, seven durable recovery cases covering
successful signature/idempotence/ledger byte preservation, missing or NULL
responses, wrong identity, changed requests/checkpoints/system prompt, invalid
attribution, malformed responses, bad attempt, stale snapshot, changed evidence,
model policy mismatch and symlink refusal. Existing isolated injected providers
retain the no-retry behavior.

## Validation and evidence class

Focused: python3 -m unittest tests.test_ceo_research_review -v
19 tests passed. focused.log contains the raw output.

Expanded: python3 -B tests/acceptance-evidence/ceo-review-recovery-20261102/validate.py
128 tests passed, exit 0. regression.log contains the full command and raw
per-test report; regression.exit records the exit status. The script archives
base HEAD inside artifacts/ceo-review-recovery-clean and overlays only the two
changed source/test files, excluding unrelated dirty implementation changes.
Existing suite ResourceWarnings are recorded in the raw report.
git diff --check passed.

These are isolated software tests using fixtures/mocks, not production
acceptance, independent provider verification or ADV certification.
ADV-001–ADV-049 and the /49 denominator are unchanged.

## Production limitation and decision

The owner reports Freelance Scope Log research-4e6018e70bf43a549e289b3f at HOLD
revision 10, a PENDING checkpoint for snapshot 888ac40a..., and a saved CEO
response. Those production facts and response validity remain independently
unverified here. The final instruction limits operations to the approved
project root; the installed checkpoint and canonical database are outside it.
A scope clarification has been requested. No install read/write, deployment,
service restart, CTKFamily mutation or production reconciliation was performed.

Accept as a source correction with isolated regression evidence only.
Production recovery remains OPEN, and no successful recommendation is claimed.
Once install scope is authorized, inspect the exact saved response without
logging secrets, correlate its hashes/request and signed snapshot/evidence,
and run the read-only recovery/validation path before considering installation.
If validation rejects it, preserve the raw response, ledger and pending intent;
report the exact validator error. A correction would require an explicitly
approved, separately attributable process using existing policy and modules.
Do not silently edit the model response, loosen validation or replay a paid call.
Independent GitHub/Claude review has not been obtained by this task.
No real CEO attachment, capital, payment, launch, external action or provider
call was performed. Unrelated dirty changes remain outside this commit.
