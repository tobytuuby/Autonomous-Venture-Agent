# Phase 1 CEO audit and executable acceptance plan — 2026-11-04

**Stage 1 audit only; no production acceptance or implementation authorization.**
Baseline: main `248f74e56dff5c8b127d034d84fc7b4d7472981d`.
Standing authority here is synthetic research only. No real venture, inference
purchase, deployment, launch, payment, key/config change or service mutation was
performed. Existing services were observed, not invoked.

## Findings and evidence classification

The existing CEO can originate proposals, establish centrally bounded research
sessions, approve Manager decomposition, review Manager-reviewed signed artifacts,
redirect/hold research, and sign a terminal disposition. Research is limited to
three rounds, four Worker reservations per round and twelve per complete proposal
digest; retries/workflow aliases do not replenish allowance. CEO and Manager model
selection is GPT-6 Sol; Worker selection is GPT-6 Luna.

This is model-mediated desk analysis, not independently verified market research.
Artifact excerpts prove attribution, not customer demand, browsing, competitor
coverage or commercial viability. The reviewed research callbacks return bounded
JSON/text; they provide no general browser/shell/product-building tool executor.
Other repository product/build code does not establish a working research-to-MVP
handoff. At R3 `PROCEED_TO_MVP` preserves a positive decision but grants no scope
or quota: `VentureWorkflow.apply` rejects further execution transitions after
disposition. The daemon skips disposed workflows. Historical
`record_mvp_blocker` records remain replayable; new blocker writes are denied.
Do not restore that obsolete write path or build a replacement orchestrator.

CEO work is strategic review, bounded direction, disposition, escalation and
financial governance within separately established limits. Manager work is task
planning, Worker assignment/correction, evidence consolidation and product
validation. Workers report through Manager. This audit neither modifies that
architecture nor establishes that production financial governance works.

### Repository and history

Initial `git rev-parse HEAD`, `git status --short` and branch inspection found
main at the baseline, no tracked modifications and numerous pre-existing
untracked runtime/evidence files. They are preserved and excluded from staging.
`git fetch origin` completed with exit 0; `HEAD...origin/main` was 0/0.
The repository is not shallow. All 491 reachable commits' subjects, local/remote
refs and advertised remote heads were inspected, with relevant source history and
patches traced; this is not an assertion that every historical diff was audited.
Remote branches include P7–P11 work; main already contains substantial later
synthetic phase history. No deleted/unadvertised remote history is claimed.

`7bf015dd7045c9bd4d955244f06c5bc2d829dec6` repairs historical signed dependent
A/B/C plan replay: historical C stays BLOCKED until A/B complete. New admission
still requires independent assignments. `248f74e` is a topology/evidence commit,
not a wholesale runtime upgrade. The reviewed hierarchy service, research daemon,
providers, gateway, runner and workflow files are unchanged between these two
revisions. Intervening `1f30440` adds existing preparation/Worker tooling and
admission hardening; it does not prove that tooling is installed or authorize
using it as a replacement.

Important history reconciliation: `phase1-implementation-plan-v1.1.md`, adopted
by `c9dc184`, records Stage 0 completion and a 2026-09-18 operator Gate 2 closure,
with provider execution still independently unverifiable. AGENTS.md still points
to v1.0/draft status. Preserve the recorded historical closure and its limitation;
do not relabel this audit as reopening/closing it. The user's “STAGE 1” means this
audit stage, not permission to activate the historical Stage 1 execution class.
Operational viability v2.4 and the bounded continuation policy retain separate
authority/review gates. Any changed requirement needs a new versioned document.

### Control: current services versus recorded installed bytes

Fresh `systemctl show` observation through venture-control:

| Unit | Enabled/state | PID / restarts |
| --- | --- | --- |
| owner-research-ceo | enabled, active/running | 288443 / 0 |
| control-broker-mtls | enabled, active/running | 288442 / 0 |
| level2d-ceo | disabled, inactive/dead | 0 / 0 |
| level2c-ceo | enabled, inactive/dead | 0 / 0 |
| ceo-exercise.timer | enabled, active/waiting | timer |

Research CEO and broker start timestamps remain 2026-11-03 01:12:09 UTC.
Their working directories are respectively
`/usr/local/lib/venture-ceo-level2c` and
`/usr/local/lib/venture-control-broker-level2c`.
The CEO ExecStart is the existing research daemon with worker-limit 4 and
`artifacts/level2c-ceo/hierarchy-config.json`; broker uses
`kernel.broker.mtls_server` with a level2c systemd drop-in.
Host-wide one-enabled-CEO acceptance is therefore still blocked.

The root-contained [topology observation](../../tests/acceptance-evidence/ceo-service-consolidation-20261104/observation.json)
records installed bytes at 13:43 UTC today. Its SHA-256 is
`63c9d6857cf819f1a29741c78fc25117bc1e9be8df02647b1360fdba0c48ac72`.
Comparing its installed SHA-256 values to all reachable changes of each path
identifies these seven older content versions:

| Installed tree | Module | Matching historical content revision |
| --- | --- | --- |
| CEO | hierarchy_service.py | 8e999120254d |
| CEO | hierarchy_providers.py | dd1dff63387c |
| CEO | provider_gateway.py | 2c66b35d668b |
| broker | hierarchy_service.py | 44ccadd89196 |
| broker | hierarchy_providers.py | cb2b56741ce3 |
| broker | provider_gateway.py | 2ee5848c3ee5 |
| broker | hierarchy_runner.py | 44b0140b870c |

The remaining six sampled copies match both 7bf015d and 248f74e, including
venture_workflow.py in both trees. These are content matches, not installed Git
checkout identities. Neither hashes nor service start time proves loaded Python
bytes. A newer disk change, uninspected module, active config drift or missing
dependency remains possible. No installed source was copied or replaced.

**Exact root limitation:** current installed source/config/trust, environment files
and live broker/CEO journals lie outside this approved project root. They were not
read. The existing inspect/observe scripts also traverse those locations (one
reads process environment); they were inspected as source, not executed.
The recorded installed hashes above are historical operator observations,
independently compared to Git now, not a fresh disk attestation.
Fresh active endpoint, policy, pins, signing trust, revocation state, capacity and
current immutable ledger/signature validity remain unverified. Do not print
environment contents, private keys, tokens or raw provider responses to fill gaps.

### Agents: parallel inspection through venture-agents only

The bridge is accessible. Its approved workspace is
`/home/epsilon/venture-agents-workspace`; `git rev-parse HEAD` returns exit 128
because it has no .git repository. Thus no installed Agents revision is proven.

Fresh service metadata showed research Manager PID 2588087, level2d Manager
2589031, level2c Manager 639231, Workers A/B/C 2589036/2589043/2589044:
all active/running with zero restarts. Research Manager and level2d Manager
share the config pathname `/var/lib/venture-manager/level2d/hierarchy-config.json`.
Workers use individual level2d configs; all use installed working directory
`/usr/local/lib/venture-manager-level2c`. Concurrent consumers need explanation,
not an assumption that duplicate work occurred.

Installed source/config/trust/journals are outside the approved Agents root and
were not read. Workspace source is a staged/historical copy, not installed
provenance; its daemon even lacks current CEO_REDIRECTION routing.
The historical workspace deployment observation reports provider_calls=0 and
ceo_started=false, not E2E completion. Agents tests/acceptance-evidence is absent.
No Agents tests, service changes, inference or file writes were performed.

### CEO → broker security and immutable evidence

Reviewed implementation: `HierarchyClient` uses HTTPS with CA validation,
hostname checking, client certificate/key, bounded messages, timeouts and denied
redirects. Broker TLS requires client certificates, TLS >=1.2, disjoint SHA-256
leaf certificate pin sets, and TLS-derived role/actor mapping. CEO reservation
identity is distinct from Manager/Worker identity. Application commands use
canonical Ed25519 signatures, pinned role trust, expiry, request identity,
revision/previous snapshot hash, proposal/version/scope and evidence bindings.
Exact committed retries converge; stale/conflicting intent fails closed.
TLS-authenticated JSON replies are not independent broker-signed attestations.

`VentureWorkflow.verify/read` reconstruct signed journal lineage.
`DurableRoleArtifactStore` checks content-addressed preparation SHA-256 on
write/read and rejects replacement/corruption. Central reservation/execution
ledgers preserve charges and reconcile exact durable intent rather than blindly
retrying paid calls. These establish mechanisms, not fresh verification of the
installed exchange. A full observation must join command signatures, artifacts,
reservation/execution records and terminal snapshot for the same proposal.

Existing root-contained multiworker execution.json records a blocked attempt,
no audit chain and restart NOT_RUN; its control observation is historical.
Later Task02/ABC/recovery reports describe other runs and fixes; do not combine
their different fixtures/dates into one successful trace. A hash manifest or
dashboard status alone cannot establish current immutable ledger acceptance.

## Ordered bounded follow-up stages (plan only)

Every stage starts with HEAD/status and a fixed source/config fingerprint; stops
on missing authority, signature, identity, ledger or provenance; preserves old
journals, counters and unrelated files. No production commands are prescribed
for this task. No new orchestrator, route around the broker, role substitution,
new grant format or Manager/Worker architecture change is needed.

1. **Provenance and contract lock — CEO audit work.** Obtain an operator-produced,
   secret-free evidence export inside the approved root using an already approved
   mechanism. Require UTC time, service properties, all imported module hashes,
   non-secret allowlisted config fields, public trust/certificate fingerprints,
   current proposal-bound approval, read-only journal verification and resource
   counts. Bind export hashes to source revision and observer provenance; classify
   unattested exports honestly. Do not copy credentials or bypass protected roots.
   Exit: exact expected/installed differences and current signed scope are
   reviewable. Separately version the phase/index reconciliation if requirements
   change. Missing export blocks production conclusions, not synthetic tests.

2. **Smallest source/test fixes — CEO boundary work.** First add a focused
   regression in tests/test_research_abc_routing.py or test_hierarchy_multi_worker.py
   for 7bf015d's historical dependent proposal → approval → A/B completion →
   C-ready replay after reopen, alongside rejection of a *new* dependent plan.
   The 7bf015d patch itself added no test. Keep original signed records unchanged.
   Add one acceptance integration test in the existing tests suite joining the
   research daemon, HierarchyClient, isolated TLS broker, workflow and artifact
   store with deterministic model callbacks. Existing unit/fixture tests cover
   the pieces but are not one complete wire-level CEO research acceptance.
   No production logic defect is proven by this audit; change runtime logic only
   if this test reproduces one, in its existing owning module.

   Installed recovery parity is a separate later deployment concern: CEO
   hierarchy_service lacks the current terminal RecoveryImpossible handling;
   hierarchy_providers/provider_gateway copies omit later proof-gated CEO pending
   recovery. Review the already committed 390f17f changes/dependencies against the
   exact installed baseline rather than implementing them again or copying main
   wholesale. Broker copies have their own older baselines listed above.
   Exit: minimal regression-backed patch, exact diff and no scope/quota expansion.

3. **Synthetic signed E2E — CEO acceptance work.** Extend existing isolated test
   mechanisms, not a daemon: generated test-only CA and role keys, loopback
   ephemeral port, root-contained temporary SQLite stores, test approval clearly
   marked synthetic, no inherited provider credentials, external network/provider
   calls denied. Use actual HierarchyClient and broker handler; deterministic
   model boundary is the only synthetic inference. Preserve Owner → CEO →
   Manager → Workers → Manager → CEO role/signature sequence.
   Run R1 decomposition, A/B/C independent submissions, Manager review, CEO
   decision; drive signed R2/R3 with distinct questions and terminal disposition.
   Also test reject, quota HOLD and Manager correction without quota reset.
   Reopen durable stores after reservation, response and apply checkpoints;
   verify one execution/terminal decision, unchanged charges and exact replay.
   Lost-response retries must preserve request identity and original allowance.

   Negative cases: no/wrong/expired certificate, wrong hostname/pin/role/signature,
   stale revision, cross-proposal/session/scope, forged digest, changed duplicate,
   journal/artifact tampering, concurrent retry, revoked approval, R4 and 5th/13th
   Worker reservation. Assert payment/launch/deploy/provider egress never occurs.
   Positive MVP disposition must remain inert with no implicit build authority.
   Exit: raw per-case results plus verified journal/artifact/ledger joins,
   synthetic classification, terminal state and explicit denied operations.

4. **Manager readiness — separate workstream, no architecture edits here.**
   Establish installed Agents source/config parity; explain which existing
   Manager consumer owns which session and test contention/idempotency.
   Validate assignment/review/correction and A/B/C evidence consolidation with
   existing Manager/Worker tests. Product/MVP readiness separately needs the
   existing authorized build scope mapped to a proposal and bounded resources,
   artifact contract, functional/browser/security checks and Manager review
   before CEO product acceptance. Research text and a recommendation are
   insufficient. Missing MVP authority stays a blocker; no repeated approval is
   invented for work already covered by exact existing authority.

5. **Reviewable synthetic acceptance package — no production activation.**
   Record commit/config/tool/prompt/runtime hashes, commands, exit codes, raw
   scenario outputs, signed synthetic commands, artifact digests, journal chain,
   reservation/execution counts, restart results and failure details.
   Add a plain-language authority/provenance/operator-impact/residual-risk
   assessment and a reviewer decision field initially NOT_REVIEWED.
   Obtain actual GitHub/Claude review evidence required by viability v2.4;
   none is supplied by this audit. Resolve findings before claiming acceptance.
   Use the existing P1 shadow certification runner for the separate 49-case
   shadow regression if this later stage requires recertification; retain raw
   ADV-001–ADV-049 results and /49. Supplemental tests never inflate /49.
   Synthetic completion proves software behavior only. Any later production
   install/restart/provider-backed acceptance requires separate scope; this plan
   supplies no production commands or production approval.

## Validation actually performed

Through venture-control, asynchronous process
`proc_mw2j0j01_ly4g2y`, PID 1447594, was polled to **exited** and its completed
root-contained output was read. Bridge process log:
`/home/epsilon/.chatgpt2localbridge/process-logs/proc_mw2j0j01_ly4g2y.log`
was not read because it is outside the approved root.

```sh
TMPDIR="$PWD/artifacts/phase1-ceo-audit-tmp" PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest \
 tests.test_broker_isolated_mtls tests.test_broker_mtls_entrypoint \
 tests.test_hierarchy_artifact_store tests.test_hierarchy_runner \
 tests.test_research_continuation tests.test_mvp_handoff \
 tests.test_ceo_pending_recovery tests.test_ceo_research_review \
 tests.test_research_poll_isolation tests.test_research_abc_routing \
 tests.test_research_broker_admission tests.test_hierarchy_service_research \
 tests.test_ceo_durable -v
```

**127 tests, 14.721 seconds, OK, exit 0.** Real loopback TLS handshakes use
generated test identities; model callbacks/authority fixtures remain synthetic.
No deployed TLS exchange, provider execution, MVP build or production acceptance
was tested. ADV certification was not rerun; /49 is unchanged.

Local raw output: `artifacts/phase1-ceo-audit-tests.log`, SHA-256
`3c8d98198e3118285cd0009fc30710fdace701d64a91d13daf2d13db9dfc07e8`;
exit file: `artifacts/phase1-ceo-audit-tests.exit`.
Full reachable history subjects: `artifacts/phase1-ceo-audit-history.txt`,
SHA-256 `431afe572bbdaef6013cf25f1238cc4446d340f75d3ff302ecea787e7ccdbe92`.
These ignored local artifacts are retained, not committed; only this audit
document is staged. This limits portability of the fresh raw execution evidence;
the exact command is provided for independent rerun. Existing tracked raw
topology evidence remains separately linked above. Documentation reference and
diff checks are required before commit.

**Decision:** audit complete with explicit evidence gaps; CEO completion,
synthetic integrated acceptance and production readiness are NOT established.
No independent approval is claimed. No real CEO was attached or invoked by this
work and no real capital, venture or external business action was used.
