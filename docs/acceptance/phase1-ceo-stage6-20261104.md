# Phase 1 CEO Stage 6 — executable deployment denial and strict dry-run

Baseline main: fe7308aa0a9d050e7ad466685e5e5a25618af972.
Decision: **DEPLOYMENT BLOCKED; production synthetic CEO acceptance incomplete**.
Review: NOT_REVIEWED. No authority requirement changes.

## Authority finding and exact existing paths

Stage4 and Stage5 reports and repository sources were read. The later legacy
unit inventory supplies the recorded installed hashes used below. All task
reads/writes were project-contained; no current installed source or production
workflow/database was read. Installed findings below therefore describe those
recorded bytes, not current disk or loaded bytecode.

The missing CEO-local resources.sqlite is consistent with intentional broker
centralization, not evidence that a new ledger should be created. The existing
broker reservation handler maps the pinned quota-ceo certificate to its fixed
actor; reserve_exchange uses the broker process's AUTHORITY_DIRECTORY, validates
standing policy and binds exchange_sessions to the exact context/policy digest.
The CEO can establish a central session there. This is a source-based conclusion
about the architecture, not verification of a current installed session.

The Stage5 CONTROL_LEDGER_V1 caller requires that same authority/session locally,
then executes through local execute_reserved. Separate installation roots and
private owner checks prevent assuming that broker authority is available to
the CEO process. Copying authority or granting cross-user access is not a fix.

Existing API assessment:

| Path | Existing behavior | Safe production proof probe |
| --- | --- | --- |
| GET /v1/hierarchy/research | Lists workflows | Avoided: exposes production work |
| GET /v1/hierarchy/state/{id} | Reads signed workflow through hierarchy gateway | Avoided: no pending workflow reads |
| GET worker research counts | CEO-only quota counts | Does not prove CEO session or exact call |
| POST /v1/inference/reservations | Pinned CEO/Manager actor; may create session and reserve quota | No: mutating, not a proof query |
| POST /v1/inference/execute | HTTP role must be poll (Manager), default execution role manager | CEO identity denied; no CEO execution binding |
| Local execute_reserved(reconcile_only=True) | Can create remote_executions and invokes reserve_exchange | No: not strictly read-only, not a CEO broker API |

The recorded installed broker helper does not support CONTROL_LEDGER_V1.
Sending the new candidate's payload is therefore not an existing compatible
route. No existing read-only session-and-exact-call validation API was found in
the inspected broker GET handler. No live POST, retry, workflow listing or
reconciliation was attempted. No Manager or Worker code changed.

## Executable result and reproducibility

Run from the project root:

```sh
sh tests/acceptance-evidence/ceo-stage6-20261104/validate.sh
python3 -B scripts/ceo_stage6_deployment_gate.py --reconstruct
```

The first command runs bounded synthetic validation. The second intentionally
exits **2**, emits deployment_allowed=false and records seven blockers.
The gate has no deployment implementation or override flag. Its source checks
are conservative necessary-capability checks, not a complete authority verifier.
Even adding matching source capabilities cannot clear fresh loaded-byte,
local binding, process isolation or independent review gaps; satisfying those
requires separately reviewed evidence and an explicit gate implementation change.

The reconstruction uses reachable Git blobs matching every recorded Python
SHA-256, writes only under artifacts/ceo-stage6-installed, and records installed
and candidate hashes in deployment-gate.json. Both recorded trees contain
**252 Python files** in total. Four CEO candidate dependencies are overlaid;
the broker candidate tree keeps all recorded broker bytes. No installation is
copied over production. No secrets, trust files, configuration or state are copied.

Strict dry-run imports deny repository fallback for agents, kernel and
integrations. The broker profile uses only broker source. The CEO profile uses
CEO candidate source and the broker-owned kernel.broker wrapper, as explicitly
shown per module in the import records. That shared-process fixture does not
prove two independent service processes or broker-agent dependency isolation.
Module __file__ paths retain the repository root solely for synthetic fixture
containment. This is exact recorded-source execution, not an actual systemd
installed-tree or loaded production process proof.

| Validation | Exact result |
| --- | --- |
| Reconstruct recorded Python source | 252 files; all match recorded hashes |
| Strict recorded broker mTLS profile | 20 tests, 7.220s, OK, exit 0 |
| Strict CEO candidate profile | 17 tests, 3.352s; 15 passed, 2 setup errors, exit 1 |
| Repository gate + recovery + candidate regression | 19 tests, 13.023s, OK, exit 0 |
| Deployment gate | BLOCKED, exit 2 (expected denial, not acceptance PASS) |
| git diff --check | Passed |

The two strict CEO errors are fixture patch-target resolution failures:
the recorded installation does not contain the integrations package used by
the existing test's external-operation denial patches. The visible AttributeError
mentions kernel.finance; ceo-imports.json records the underlying denied
integrations imports. No repository fallback was added to conceal this gap.
Thus strict installed candidate acceptance remains **unverified**, rather than
a claimed production failure or a passing synthetic acceptance.

Synthetic tests use fake responses, temporary test signers and loopback TLS;
Internet socket connections are denied. They do not use the production identity.
Stage4's earlier real CEO mTLS evidence is historical, not freshly reverified.
No provider execution is independently verified by this task.

The validation command started asynchronously as proc_mw2o5435_tcpnq9,
PID 2187041, bridge log
/home/epsilon/.chatgpt2localbridge/process-logs/proc_mw2o5435_tcpnq9.log.
It was observed exited and completed project-contained logs were read through
venture-control. Full command, raw per-test reports, import provenance, exits,
and SHA256SUMS are retained beside this report's evidence directory.

## Scope and operator decision

Changes: scripts/ceo_stage6_deployment_gate.py, tests/test_ceo_stage6_gate.py,
this report, and tests/acceptance-evidence/ceo-stage6-20261104.
Only an offline gate and synthetic tooling are added. No runtime fix is proven
safe within the existing API/process boundaries, so no production deployment
or restart is performed. The gate is a reviewable release prerequisite, not an
installed systemd interlock. Active services are not freshly attested.

Real ventures, signed state, ledgers and existing untracked user files were not
modified. No production pending workflow was read, replayed or repaired.
No real CEO was attached/enabled, no external provider call, capital, payment,
launch or external venture action was initiated. ADV-001–ADV-049 and /49 remain
unchanged. GitHub/Claude review, fresh installed proof and safe process isolation
remain open. A globally clean worktree is not claimed because pre-existing
untracked runtime/evidence files are preserved.
