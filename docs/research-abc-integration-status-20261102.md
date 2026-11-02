# Research A/B/C routing integration — 2026-11-02

Implementation and isolated validation report, not production acceptance or a policy change.
Starting main: a8500e692823af755cdcaf428c9e491e47132a24.

## Scoped implementation

- owner_research_kickoff.py signs new preparation scopes with worker-a.
  Existing workflow snapshots return unchanged; no migration or re-signing occurs.
- hierarchy_research_daemon.allowed_config supplies the fixed Manager decomposition
  mapping A=worker-a, B=worker-b, C=worker-c in the research task configuration copy.
  The configured primary workflow (including Client Document Checklist) is unchanged.
- Existing ModelRoleCallback, HierarchyRunner and VentureWorkflow still construct,
  sign, approve, persist and enforce the decomposition. C depends on A and B.
- The daemon checks exact actors, configured mappings and assignment dependencies.
  Workers require a CEO-approved ready assignment. Retired service-worker cannot
  execute research. Legacy service-worker scope references remain readable so
  historical signed research records need not be rewritten.
- No quotas, broker policy, services, signed workflow records or deployment files
  were changed. No real CEO, provider inference, capital or external business action
  was used. ADV-001–ADV-049 and /49 remain unchanged.

Changed implementation/test files: agents/ceo/hierarchy_research_daemon.py,
scripts/owner_research_kickoff.py, tests/test_research_abc_routing.py.

## Validation and provenance

Command (Python 3.14.4, fake inference and local fixture keys only):

```sh
python3 -B -m unittest \
  tests.test_research_abc_routing tests.test_hierarchy_multi_worker \
  tests.test_hierarchy_service_research tests.test_owner_research_quota_hold \
  tests.test_research_continuation tests.test_worker_inference \
  tests.test_hierarchy_gateway tests.test_hierarchy_runner \
  tests.test_hierarchy_model_callbacks tests.test_hierarchy_redirection \
  tests.test_venture_workflow tests.test_manager_review_budget \
  tests.test_preparation_broker tests.test_hierarchy_bootstrap -v
```

Clean HEAD archive plus the three scoped implementation/test files:
**135 tests, OK, exit 0**. Archive and test temporary directory stayed inside the
approved project root. This isolates validation from pre-existing dirty changes.

Same command in the original dirty tree: **135 tests, 125 passed, 10 errors,
exit 1**. All ten errors arise from the pre-existing admission fixture's duplicate
pinned key for service-worker and worker-a. Running test_research_continuation
with the original HEAD daemon and kickoff restored in memory reproduced the same
ten errors (11 tests, one passed). That dirty fixture was left unchanged.

An initial 15-test focused run had one new-fixture error (missing revision);
the fixture was corrected before the complete clean validation above.

Raw logs, exit codes and SHA256SUMS are retained locally in
artifacts/ava-abc-research-20261102/ (ignored validation artifacts, not pushed).
git diff --check passed. Hash comparison confirmed all 644 accessible
pre-existing dirty files unchanged; inaccessible runtime contents were not
independently inspected.

## Remaining integration and deployment work

Deployment was withheld. Installed CEO, Manager and A/B/C worker configurations,
trust, policy alignment and service bindings could not be independently verified
inside the approved project root. Repository research unit definitions refer to
installed paths outside it and still include a legacy single-worker unit.
No installed configuration was read or changed.

Committed HEAD broker research admission still requires service-worker. A
pre-existing uncommitted hierarchy_gateway.py change instead requires worker-a.
That change is preserved and excluded from this patch; new kickoff against an
unchanged legacy broker will fail closed. Review and integrate that existing
admission work separately before deploying this kickoff. Do not infer alignment
from successful mocked kickoff tests.

Existing research already delegated to the retired worker without decomposition
will now remain blocked. It requires an authorized signed supervisory transition;
this patch does not rewrite it. Existing signed Client Document Checklist work
must retain its bindings and evidence.

After configuration and admission alignment is independently established, reuse
the existing services, then collect genuine signed CEO → Manager → A/B → C →
Manager evidence, including the required second research round. GitHub/Claude
review and runtime/independent production acceptance remain outstanding.
No live reachability or production completion is claimed.
