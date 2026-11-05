# P1-04 C1 broker maintenance — v1.0

C1 adds opt-in host-local admission and drain to the existing broker. This is source readiness with synthetic evidence, not production acceptance or authority. Maintenance control is disabled by default on production startup when both configuration keys are absent; this task neither inspected nor changed production configuration. Stage6 remains **DENY**. No Manager/Worker role entry paths are added.

## Provisioning and use

Provision only in a separately authorized operation, before any participating broker starts:

1. Use a canonical absolute path with no symlink components on a local filesystem supporting Linux advisory `flock`, `pread/pwrite`, and `fsync`. Ancestors must be owned by root or the broker effective UID. Root and that UID are trusted.
2. Create a dedicated directory owned by that UID with mode 0700. Inside it create a single-link regular control file with mode 0600 and exact bytes `CLOSED\n`, and a separate single-link regular file named `<control>.active`, mode 0600, with zero bytes. Persist the files and directory during provisioning; do not replace them afterward.
3. Record decimal device/inode pairs, in order: control, active file, directory. Join the six numbers with colons. Set `VENTURE_BROKER_MAINTENANCE_CONTROL` to the absolute control path and `VENTURE_BROKER_MAINTENANCE_IDENTITY` to that identity for every participant. Either key being present requires both nonblank values; partial configuration fails startup.
4. Use `MaintenanceAdmission(path, identity)` from `kernel.broker.isolated_mtls` in an explicitly authorized local operator process under the same UID. `with gate.drain(timeout): ...` persists CLOSED, waits for all admitted activity, and holds exclusive activity through the maintenance body. Exit, timeout after closure, exceptions, and operator death never automatically reopen it.
5. After successful maintenance and independent safety checks, explicit `gate.release(timeout)` requires valid CLOSED and exclusive zero activity before persisting OPEN. Initial startup likewise requires explicit release: CLOSED denies before configured constructors run. Never truncate, recreate, unlink, rename, edit state directly, or refresh inode pins to bypass a denial.

The activity file is only an advisory lock; neither file is an execution, reservation, quota, or financial ledger. Timeouts accept finite numeric seconds from 0 to 300; request admission waits at most 0.25 seconds for the control mutex. Every participating process must share the same configuration and files.

## Reviewed behavior and fail-closed limits

Admission and activity acquisition share the control mutex with closure. The shared activity lease begins before HTTP parsing and covers existing identity checks, all callback families, body reads, durable callback completion and response writes. Existing mTLS and role restrictions still apply. Closed, malformed, missing, substituted, linked, wrongly owned or incorrectly permissioned control artifacts cannot grant admission. Requests receive a best-effort 503 maintenance denial; early TLS closure can instead produce a broken pipe/reset/disconnect while the client is sending. The synthetic wire assertions accept those refusal outcomes and verify callbacks/ledger/provider counts remain unchanged.

Drain succeeds only after acquiring exclusive activity and rechecking CLOSED. A timeout before closure is persisted does **not** prove CLOSED; any failed drain means HOLD, never permission to maintain. In-flight work is allowed to finish, not cancelled. Slow request parsing, response I/O, or callbacks may prevent drain from completing. TLS handshakes and unadmitted socket handling are outside the activity lease; drain is not a listener shutdown or denial-of-service guarantee.

Filesystem or persistence errors deny success and attempt a best-effort CLOSED rewrite. If storage also prevents that rewrite, durable closure cannot be guaranteed; keep HOLD and require independent authorized recovery. Advisory locks do not constrain uncooperative writers, direct ledger access, processes without this opt-in, root/same-UID tampering, or other hosts. File/inode replacement requires separately authorized reprovisioning with all participants stopped; no automatic recovery or pin refresh exists.

## Validation and decision

The previous focused3 log was inspected: 25 tests, exit 0. Final validation is recorded below after completion. Raw per-test logs, exits, strict import provenance and reconstruction scripts remain local under `tests/acceptance-evidence/p1-04-c1-20261105/`; they are deliberately excluded from this commit.

| Check | Result |
| --- | --- |
| Complete source broker/CEO regressions, including C1, replay, quota, roles, crash/restart, installed fallback and Stage6 guards | 220 tests, 0 failures/errors, exit 0 (final-regression3.log) |
| Strict unchanged recorded broker mTLS | 20 tests, 0 failures/errors, exit 0 |
| Strict C1 broker candidate: full mTLS/startup plus C1 admission and TLS classes | 44 tests, 0 failures/errors, exit 0 |
| Strict CEO candidate: full broker, pending recovery, candidate acceptance and C1 ledger replay classes | 31 tests, 0 failures/errors, exit 0 |
| Python syntax and git diff --check | exit 0 |

Source command: `TMPDIR="$PWD/artifacts/p1-04-c1-final-tmp" PYTHONPATH="$PWD:$PWD/tests" PYTHONDONTWRITEBYTECODE=1 python3 -B tests/acceptance-evidence/ceo-stage5-20261104/verify_synthetic.py` followed by all 24 modules listed in the local final regression process record: `tests.test_{broker_maintenance_c1,broker,broker_isolated_mtls,broker_mtls_entrypoint,preparation_broker,research_broker_admission,ceo_broker,ceo_research_mtls_acceptance,ceo_candidate_acceptance,ceo_pending_recovery,ceo_queue_recovery,ceo_research_review,ceo_three_round_mtls,ceo_legacy_dependent_replay,ceo_installed_compatibility,ceo_stage6_gate,deployment_broker_restart,ceo_gates,ceo_durable,ceo_shadow,ceo_provider,ceo_provider_entrypoint,ceo_escalation_inbox,ceo_venture_flow}` (brace notation expands to individual module arguments). Strict checks: `python3 -B tests/acceptance-evidence/p1-04-c1-20261105/final_installed2.py`, which records each exact subprocess command and imported file hash.

The first source attempt failed discovery because PYTHONPATH was omitted (24 import errors); corrected runs passed 220 tests. The first strict broker candidate run had one BrokenPipeError in the pre-parse denial assertion; the corrected refusal assertion passed in the fresh strict rerun above. No execution or role boundary was relaxed. Process completion and completed logs were inspected through venture-control.

The strict checks reconstruct fresh project-contained trees from hash-verified P1-03 recorded bytes and explicitly overlay only the two C1 broker files. Protected imports cannot fall back to the checkout; existing fixture-only payment import dependencies remain synthetic denial targets. These checks do not inspect current installations, loaded production bytes, live provider execution, services, pending work or live ledgers. The source suite also uses the existing loopback-only network guard and project-contained temporary storage.

Review decision: C1 source may be committed only with the listed passing checks. Production provisioning, adoption, loaded-byte/work isolation evidence and independent GitHub/Claude review remain outstanding; C1 grants none of those approvals. This is supplemental local synthetic evidence, including real loopback TLS and process-death tests; ADV-001–ADV-049 and the /49 denominator are unchanged.

Only `kernel/broker/isolated_mtls.py`, `kernel/broker/mtls_server.py`, `tests/test_broker_maintenance_c1.py` and this document belong to C1. The unrelated dirty `agents/ceo/deployment_pause.py` is preserved at SHA-256 `4aa2fa78cba1d59df098d3127d7ef2c4bc0f2bf713855246bebd2823447128e9`. No real CEO, capital/payment action, live ledger access, service operation or deployment was used.
