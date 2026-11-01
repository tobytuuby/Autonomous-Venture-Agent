# Task03 cleanup validation evidence — 2026-11-01

Scope and review decision: [cleanup v1.3](task03-corrective-cleanup-v1.3.md).
Executed through the `venture-control` bridge inside
`/home/epsilon/venture-control-workspace`.
Initial and final HEAD: `c8fab3674b434a1fce2b54428b7e3a0de66911cc`, `main`.
No commit, push, deployment, production attachment or external/capital action.

## Observed results

| Run | Exact result | Local raw log |
| --- | --- | --- |
| Unchanged quota-hold baseline | 1 test, 1 error; exit 1; 0.028s | `baseline-quota-hold.log` |
| Initial focused iteration | 25 run, 1 import error; exit 1; 2.515s | `focused.log` |
| Second focused iteration | 31 run, 2 assertion failures; exit 1; 4.711s | `focused-final.log` |
| Final focused verification | 33 tests passed; exit 0; 5.212s | `focused-verified.log` |
| Expanded regression | 167 tests passed; exit 0; 20.934s | `regression.log` |

The baseline error is `authoritative research proposal required`, independently
reproduced in this local unchanged fixture before edits. The fixture repair and
its zero-reservation negative case are explained in v1.3.

The initial edit accidentally removed the adjacent `poll` declaration with the
retired function; restoring it resolved the import error. The second iteration's
two denial assertions expected the wrong guard: a changed historical request was
still bound to a stale snapshot, and its Worker was not the assigned Worker.
The final tests issue a freshly bound blocker and use the assigned Worker,
verifying the intended retirement and post-disposition guards. These failures
are retained, not counted as passes.

## Coverage and provenance

The final focused run includes generated signed historical blocker reconstruction
and exact receipt replay after reopening SQLite; changed requests and invalid
signatures denied; new CEO/Manager/Worker blocker submissions denied by gateway
and direct journal admission; post-disposition Manager/Worker/finance/continuation
denial without a blocker; daemon skipping positive, historical-blocker and
terminal histories; Owner status equivalence with/without the historical record;
and recomputed-hash forgery rejection.

The historical fixture seeds a private temporary journal with the original
deterministic snapshot fields and a generated CEO signature using the existing
private record writer. It does not call current public admission to create a
blocker or change production history. Restart verification independently
reconstructs that fixture and checks its signature and state.

Expanded tests retain shared and cumulative broker quota denials, reservation
replay/conflict checks, workflow/runner/broker enforcement, approved research
integration, Owner API and positive disposition tests. Existing
`test_task03_existing_owner_authority.py` is included unchanged.

All execution here is isolated implementation evidence with fake providers,
generated test keys and temporary journals/ledgers. Test work is under project-local
TMPDIR. It does not establish current production authority, live provider
reachability, genuine MVP execution, independent Claude acceptance or deployment.
Financial values remain unavailable; no payment or financial approval was issued.
ADV-001–ADV-049 and /49 remain unchanged; no ADV certification was run.

## Exact commands and asynchronous process records

Initial inspection:
```sh
git rev-parse HEAD && git status --short && git branch --show-current && cat AGENTS.md
```

`rg` was attempted for discovery but is unavailable in the bridge environment;
bounded `find` and `grep` were used afterward. That inspection-command error
is unrelated to test results.

Every test process was started asynchronously, recorded by ID/PID/log path,
polled through the bridge process list to `exited`, then its completed
project-local raw log and exit file were read through the bridge. The bridge's
out-of-root process log paths were recorded only as metadata, never read.

Exact start commands, in run order:
```sh
TMPDIR="$PWD/artifacts/task03-cleanup-20261101/tmp" infrastructure/python-runtime/.venv/bin/python -B -m unittest tests.test_owner_research_quota_hold -v > artifacts/task03-cleanup-20261101/baseline-quota-hold.log 2>&1; result=$?; echo "$result" > artifacts/task03-cleanup-20261101/baseline-quota-hold.exit; exit "$result"
TMPDIR="$PWD/artifacts/task03-cleanup-20261101/tmp" infrastructure/python-runtime/.venv/bin/python -B -m unittest tests.test_mvp_handoff tests.test_ceo_research_review tests.test_research_continuation tests.test_owner_research_quota_hold -v > artifacts/task03-cleanup-20261101/focused.log 2>&1; result=$?; echo "$result" > artifacts/task03-cleanup-20261101/focused.exit; exit "$result"
TMPDIR="$PWD/artifacts/task03-cleanup-20261101/tmp" infrastructure/python-runtime/.venv/bin/python -B -m unittest tests.test_mvp_handoff tests.test_ceo_research_review tests.test_research_continuation tests.test_owner_research_quota_hold -v > artifacts/task03-cleanup-20261101/focused-final.log 2>&1; result=$?; echo "$result" > artifacts/task03-cleanup-20261101/focused-final.exit; exit "$result"
TMPDIR="$PWD/artifacts/task03-cleanup-20261101/tmp" infrastructure/python-runtime/.venv/bin/python -B -m unittest tests.test_mvp_handoff tests.test_ceo_research_review tests.test_research_continuation tests.test_owner_research_quota_hold -v > artifacts/task03-cleanup-20261101/focused-verified.log 2>&1; result=$?; echo "$result" > artifacts/task03-cleanup-20261101/focused-verified.exit; exit "$result"
TMPDIR="$PWD/artifacts/task03-cleanup-20261101/tmp" infrastructure/python-runtime/.venv/bin/python -B -m unittest tests.test_mvp_handoff tests.test_ceo_research_review tests.test_research_continuation tests.test_worker_inference tests.test_hierarchy_gateway tests.test_hierarchy_runner tests.test_hierarchy_model_callbacks tests.test_hierarchy_multi_worker tests.test_hierarchy_redirection tests.test_venture_workflow tests.test_hierarchy_service_research tests.test_owner_research_progress tests.test_owner_research_quota_hold tests.test_owner_research_admission tests.test_manager_review_budget tests.test_preparation_broker tests.test_hierarchy_bootstrap tests.test_owner_idea_inbox tests.test_owner_research_feedback tests.test_task03_existing_owner_authority tests.test_owner_api -v > artifacts/task03-cleanup-20261101/regression.log 2>&1; result=$?; echo "$result" > artifacts/task03-cleanup-20261101/regression.exit; exit "$result"
```

| Run | Bridge ID | PID |
| --- | --- | --- |
| 1 | `proc_mvydfj4k_mf5n5h` | 2557207 |
| 2 | `proc_mvydhf56_0r0ldg` | 2561044 |
| 3 | `proc_mvydi3x2_zqdfow` | 2565711 |
| 4 | `proc_mvydj28l_dvgekj` | 2566172 |
| 5 | `proc_mvydjts4_iofs4b` | 2570872 |

For each ID, the bridge returned process-log metadata
`/home/epsilon/.chatgpt2localbridge/process-logs/<ID>.log`.
Exact returned metadata is also retained in the local `processes.json`.

## Artifacts, hashes and preservation

Raw per-test output, adjacent exit files, `processes.json`,
`baseline-dirty.json`, `preservation.json` and final `verification.json`
are in ignored `artifacts/task03-cleanup-20261101/`.
They are local evidence, not a pushed shared review record.

SHA-256 of completed raw logs:
```text
8e02339df4d6af1ae2d28790073b13320d05a01056a51fab9e8cc86fe3d64027  baseline-quota-hold.log
391fcfcf5c547b7bfdcb7757efa5d8a3468e69c02f71f67738d12867a58ba56e  focused.log
22c915c5ffee2b86b9246327e72d900beaa62094f86c4a61da292cb8bf4031d5  focused-final.log
c61be7d22ec71bf9be94fd95cfb8b43df21c9540480580c2eff2d4ddbc79017f  focused-verified.log
a075ff9ce03f54bb6aa6ee2ca5b7dc0bfc1df550ab18fc7a4c65268eb91a5863  regression.log
```

Before edits, SHA-256 baselines captured 641 readable files enumerated from the
dirty status (including readable files inside collapsed untracked directories).
After edits, all 641 matched; no changed baseline files were found. This
preservation claim covers readable enumerated files only, not inaccessible or
unenumerated production authority. The worktree remains intentionally dirty.

Final checks:
```sh
git diff --check
git rev-parse HEAD
git status --short
```

Final reference/hash/preservation checks and exact changed-file inventory are
recorded in `verification.json`; the two cleanup documents link to existing
project files. No historical documentation or signed production record was
rewritten. User instructions explicitly prohibit commit/push/deploy for this
cleanup, so earlier general publish/deploy workflow requirements were not applied.
