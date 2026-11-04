# Phase 1 CEO Stage 4 — source provenance and safe reconciliation decision

Baseline: main `a0c615e707f13c981160c40a9e79023397a84e7c`.
Control VM only, through venture-control. Reviewer decision: **NOT_REVIEWED**.
**Deployment withheld: unsafe recovery ambiguity and incomplete dependency binding.**
No runtime fix is established as safe to deploy in this scope.

This supplements [Stage 1 audit](phase1-ceo-audit-20261104.md),
[Stage 3](phase1-ceo-stage3-20261104.md) and
[topology v1.0](../ceo-service-topology-v1.0.md); it changes no authority or acceptance requirement.
The owner's standing authorization covers internal synthetic testing/deployment,
but requires preservation of concurrent research and no external costs.

## Fresh provenance and delta decisions

Fresh installed source reads, SHA-256 comparisons and reachable per-path Git
history comparisons reproduce all seven historical content matches. Exact full
installed/HEAD hashes, imports and history commits are in
[observation.json](../../tests/acceptance-evidence/ceo-stage4-20261104/observation.json).
[source-deltas.json](../../tests/acceptance-evidence/ceo-stage4-20261104/source-deltas.json) contains the exact unified installed-to-baseline deltas as JSON strings.
These are disk content identities, **not** proof of loaded Python bytecode.

| Tree / file | Historical content | Decision for this task |
| --- | --- | --- |
| CEO hierarchy_service.py | 8e999120254d | Two diagnostic codes only; optional observability, no recovery capability |
| CEO hierarchy_providers.py | dd1dff63387c | Tracked CEO recovery is needed for pending-call acceptance; cannot install alone |
| CEO provider_gateway.py | 2c66b35d668b | Needed by tracked local CEO recovery; includes Manager changes, so whole-file parity is not a minimal approved fix |
| Broker hierarchy_service.py | 44ccadd89196 | Role polling/recovery changes are not required by the running broker HTTP entrypoint; do not copy |
| Broker hierarchy_providers.py | cb2b56741ce3 | Role client behavior, including Manager changes; not justified for the broker HTTP service |
| Broker provider_gateway.py | 2ee5848c3ee5 | Existing Manager reconciliation already present; new local CEO branch is not needed by Manager-only HTTP dispatch |
| Broker hierarchy_runner.py | 44b0140b870c | Terminal-disposition early return is useful defense, but does not justify a broker restart for the observed HTTP path; workflow rejects new execution transitions |

Static import traversal sampled 84 module references across the two trees.
[readiness.json](../../tests/acceptance-evidence/ceo-stage4-20261104/readiness.json)
records dependency hashes and drift. This is conservative static evidence, not a
complete dynamic import graph: package/symbol references can appear as missing
modules. A real missing broker ceo_research_review.py also prevents assuming that
the broker tree supports the new local CEO branch. No source tree was bulk copied.

Required dependency work extends beyond the seven files:

- CEO ceo_research_review.py lacks the new metered pending-response recovery.
  Installing providers alone leaves that caller on the old manual-reconciliation path.
- Both installed provider_reservation.py copies lack execution_mode validation
  and the existing_session_only keyword. The new provider caller cannot safely
  use the old helper. Corresponding dependency diffs are retained.
- CEO resources.sqlite is absent at its installed authority directory; the
  broker-owned ledger exists in the separate broker tree. New local recovery
  must prove it reaches the existing authority/session/ledger with the correct
  service permissions. Creating a new authority, copying a ledger, resetting
  state or weakening root/ownership checks would invalidate the evidence.
- service_identity.py also differs in directory-mode enforcement. That security
  delta was inspected, not silently copied or relaxed.

These are necessary capability/dependency findings, not a validated deployment
manifest. No new architecture, Manager behavior, credential configuration,
security boundary or authority rule was introduced.

## Exact blocker and live read-only evidence

The active workflow research-5900c3db9bb5bd74601e3f9d is CEO_REVIEW revision 9.
Its research-review-inference.sqlite contains one call with NULL response:
ceo-89ea3a74cf4d4b40aa2c80c94f0c068deffd648a49690ce2ea.
The request digest is
98a06ea21e1c2a44739f0585f7afffdacd16b0797e5a45bce9289ee716d5b96f.
Its original attempt is retained; only an attempt hash is exported.

A read-only identity join finds **no matching central reservation or execution
row** for that pending call. The broker separately contains one PENDING remote
execution; it is not identified as that CEO call. Missing reservation evidence
does not authorize inventing a completed response or replaying legacy inference.
The absent local authority binding and old helper/caller mean that seven-file
replacement cannot establish exact safe recovery. Restarting newer recovery
could also enter an inference path, contrary to this task's no-external-cost
constraint. Leave the pending intent, identities, charges and session untouched.

[verified-readonly.json](../../tests/acceptance-evidence/ceo-stage4-20261104/verified-readonly.json)
records a fresh real loopback mTLS GET using the installed certificate under
venture-ceo, UID 993, actor service-ceo. Proxies were disabled and endpoint
asserted to be https://localhost:8443; no POST or provider call was made.
The installed certificate subject is CN=venture-level2c-ceo, SHA-256
779a51031675c0f667522e8a680b11fd64e93fc7624382396176dd4c81701063.
This freshly confirms the CEO read path; the previously proven Manager/Workers
role evidence is not repeated or expanded here.

Offline verification with the baseline workflow verifier and installed public
actor trust verified all 134 signed audit records and 13 workflow snapshots.
All six live research snapshots joined exactly to that verified journal.
Public trust was independently parsed for evidence, with owner/mode checks;
no deployed root restriction or trust configuration was changed.

| Ledger count | Before | After |
| --- | ---: | ---: |
| Daily reservations table (all rows) | 157 | 157 |
| Remote reservations | 105 | 105 |
| Remote executions | 51 | 51 |
| Worker reservations | 52 | 52 |
| Worker executions | 52 | 52 |
| Worker research charges | 39 | 39 |

Remote executions comprise 50 COMPLETE and one PENDING. The broader readiness
probe also observed 105 exchange_calls and 23 exchange_sessions, unchanged.
Counts are read-only observations around the probes, not a lock or promise that
ongoing services cannot later advance. No prompts, model results, signing
secrets, private key contents or environment values were exported.

## Service decision and rollback plan

Final active services remain research CEO PID **288443**, broker PID **288442**;
both NRestarts=0 and start time 2026-11-03 01:12:09 UTC.
[final-state.json](../../tests/acceptance-evidence/ceo-stage4-20261104/final-state.json)
confirms all seven installed SHA-256 values remain identical to the fresh
observation. The research CEO Requires/After the broker; both have control-group
kill mode and 90-second stop timeout. A broker restart therefore cannot be
treated as an isolated harmless action for concurrent CEO work.

No backup/install/restart/reset command was issued. No rollback is needed.
For any later approved reconciliation, first prove the exact active
authority/session path and pending outcome, prohibit inference during
maintenance, and validate an isolated candidate with installed dependencies.
Back up only the agreed files inside the approved project root, recording
original bytes, SHA-256, owner/group/mode and exact target path. Compare expected
preimage hashes immediately before an atomic replacement; preserve units,
configuration, trust and all databases. Restart only the affected service after
proving it cannot consume outstanding work or trigger paid inference.
If health/identity/signature/count checks fail, restore precisely those file
preimages and metadata and restart only that service. Never restore old database
snapshots over concurrent research. If quiescence or accounting cannot be proved,
withhold deployment as done here. This is a plan, not an executable authorization
to replay the current pending call.

## Validation, failures and remaining gaps

The focused command used a root-contained TMPDIR, disabled bytecode and a
120-second bound:

```sh
TMPDIR="$PWD/artifacts/ceo-stage4-tmp" PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$PWD:$PWD/tests" timeout 120s python3 -B -m unittest \
 tests.test_ceo_pending_recovery tests.test_research_recovery \
 tests.test_ceo_research_mtls_acceptance tests.test_ceo_three_round_mtls \
 tests.test_research_poll_isolation tests.test_hierarchy_providers -v
```

Before decision: **44 tests, 26.143 seconds, OK, exit 0**.
After inspection: **44 tests, 25.903 seconds, OK, exit 0**.
Both runs are synthetic: fake inference, test signers and temporary loopback TLS.
They do not prove installed hybrid recovery or OS process-restart acceptance.
No ADV rerun; ADV-001–ADV-049 and /49 are unchanged.

Inspection tooling had two corrected local failures: inspect.py shadowed the
stdlib inspect module (renamed source_provenance.py), and the repository
load_trust helper correctly rejected an installed path outside its own root
(replaced for offline evidence by explicit public-trust parsing). Runtime
security checks were not patched. A separate bounded dependency query reported
the absent broker CEO review module. Original failed logs remain local.
Final successful evidence and raw per-test logs are retained with SHA256SUMS;
process records list asynchronous starts, exited observations and root-contained
logs. Summary records do not replace the raw evidence.

Evidence classification: direct Control source/service/ledger observation,
authenticated live read-only CEO exchange, independent offline signature
verification, and synthetic software tests. This does not independently verify
provider execution, production acceptance or a safe installed restart.
Pending legacy outcome, authority/ledger binding, installed candidate validation,
host-wide CEO topology, MVP/build scope and actual GitHub/Claude review remain
open. Reviewer decision remains NOT_REVIEWED.

Only the new evidence directory and this document change. Pre-existing untracked
runtime/evidence files are preserved; a globally clean worktree is not claimed.
No real CEO was attached/enabled, no production source was replaced, no service
was restarted, and no capital, payment, launch, external business action or
paid inference was initiated by this task.
