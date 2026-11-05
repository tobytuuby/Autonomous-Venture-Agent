# P1-03 installed runtime compatibility — 2026-11-05

Decision: close the two strict candidate setup errors for isolated recorded-source execution. Production acceptance and deployment remain blocked. This changes no authority or orchestration policy.

Starting main: be2feea928b360d60cffe57f98a067b837e0f9ec. HEAD, branch and status were inspected through venture-control. No tracked changes existed; numerous unrelated untracked files, including the prior attestation, were preserved.

## Exact diagnosis and minimal correction

Both errors were in CEOCandidateAcceptanceTests:
- test_three_round_process_exit_recovery_preserves_signed_trace_and_quota
- test_two_created_synthetic_ventures_reject_cross_bound_reservation

Both failed in inherited ResearchMtlsAcceptanceTests.setUp at the external-operation denial patch loop, before either test body. Resolving kernel.finance.finance.FinancialGovernor.allocate imports kernel.finance.__init__, which eagerly imports payment_path, which imports integrations.payment_adapter. The attested CEO tree has no integrations directory. The strict finder raises ImportError for integrations; pkgutil.resolve_name catches it while resolving the dotted patch target and ultimately reports AttributeError: module 'kernel' has no attribute 'finance'. The original 20261105 ceo-imports.json records exactly two denied integrations imports.

The isolated candidate now explicitly packages these three existing, committed source files in each candidate profile:
- integrations/payment_adapter/__init__.py
- integrations/payment_adapter/real.py
- integrations/payment_adapter/simulated.py

They supply the existing fixture's denial patch targets and transitive finance initializer dependencies. No adapter is instantiated or invoked by packaging. The denial patches remain unchanged. No production package, service, configuration, authority file, ledger, quota or key was copied or modified.

This is a test dependency closure. No agents/ceo or kernel/broker source imports kernel.finance or integrations.payment_adapter. These tests therefore do not establish a new live CEO/broker payment dependency. Importing the existing kernel.finance package itself does require the adapter because of its eager initializer; any future installation exposing that package must include this existing dependency. No lazy-import redesign is needed for this task.

scripts/ceo_strict_installed_dry_run.py is a reusable copy of the preserved fresh strict harness with explicit project-contained tree/output arguments, import provenance and rejection of preloaded protected packages. It never reads production installation paths. Every agents, kernel and integrations import must resolve in the selected isolated profile. Repository-shaped __file__ values exist solely for synthetic root checks; missing modules raise before Python can search the checkout. The new subprocess regression tests three absent modules, including package children whose __path__ points at the checkout, and proves all three fail closed.

After packaging, pkgutil also probes integrations.payment_adapter.RealPaymentAdapter as if it were a submodule, then resolves the exported class attribute after catching ImportError. Raw import records retain these denied probes. They are expected attribute-resolution probes, not missing package dependencies or setup errors; finalization permits only that exact exported-class name.

## Source to installed matrix and scope

The exact matrix is tests/acceptance-evidence/p1-03-installed-compatibility-20261105/source-installed-module-matrix.json. Each row records profile, module, path, source SHA-256, attested installed SHA-256 (null when absent), isolated candidate SHA-256, origin and observed test requirements.

| Profile | Matrix rows | Distinct observed modules | Explicit Stage7 overlays | Added guard dependency files |
| --- | ---: | ---: | ---: | ---: |
| CEO | 130 | 55 | 8 | 3 |
| Broker | 128 | 42 | 8 | 3 |

The eight explicitly pinned existing Stage7 overlays in each profile are agents/ceo/{ceo_broker,ceo_research_review,hierarchy_client,hierarchy_providers,provider_gateway,provider_reservation}.py and kernel/broker/{isolated_mtls,mtls_server}.py. This task changes none of their bytes. ceo_broker.py is absent from the recorded installations. All other candidate bytes match the attested installed hashes except the three explicitly added fixture dependencies. The untouched recorded broker test imports 38 modules. Namespace directories have no fabricated source hash; integrations is created by explicitly packaging its child files.

An exploratory combined broker suite failed collection of tests.test_ceo_broker because the recorded broker tree lacks agents.ceo.hierarchy_research_daemon. That suite inherits the CEO daemon fixture and belongs in the CEO profile; it is not evidence of a broker runtime dependency. The existing strict CEO profile runs it successfully. The failed attempt is preserved under attempts/expanded-broker-scope; no cross-profile imports or extra broker modules were allowed.

## Validation and evidence

| Execution | Result |
| --- | --- |
| Before explicit fixture packaging | 17 tests, 15 passed, exact original 2 setup errors; expected exit 1 |
| Strict candidate CEO recovery and candidate acceptance | 17/17, zero failures/errors, exit 0 |
| Strict candidate CEO broker-route suite | 12/12, zero failures/errors, exit 0 |
| Strict recorded installed broker mTLS | 20/20, zero failures/errors, exit 0 |
| Strict candidate broker mTLS and startup gates | 30/30, zero failures/errors, exit 0 |
| Focused source regression: fallback, Stage6 denial, pending recovery, candidate acceptance | 20/20, exit 0 |
| git diff --check and staged diff check | exit 0 |

The full commands, raw per-test reports, exits, import hashes, result manifest, historical input hashes, process records and SHA256SUMS are in tests/acceptance-evidence/p1-03-installed-compatibility-20261105/. validate.py reconstructs project-only test trees from the existing hash-verified local recorded snapshots and explicit Git overlays; finalize.py verifies the completed evidence without rerunning inference or tests. Reproduction requires those prior local snapshots and historical input evidence; the matrix and raw execution/import records are committed here. New isolated trees are deliberately required to prevent stale module reuse.

Validation was started asynchronously through venture-control, polled to exited, and completed project logs read through that bridge. Process details include the initial reconstruction bookkeeping failure, the overly broad broker-suite attempt, and a post-test evidence assertion that initially mistook the exported-class probes for absent modules. These attempts were corrected and retained; passing final executions were not replaced by summaries. No warnings were emitted in the four final strict suite logs.

Evidence classification: independently observed local synthetic execution using hash-verified recorded installed Python bytes plus explicit candidate/test overlays. Models, owner approval, signers and ledgers are synthetic fixtures under the project; TLS is real loopback TLS. This is supplemental evidence only: ADV-001–ADV-049 and /49 are unchanged.

Limits: no current installed source, loaded production bytecode, live provider, active/pending production work or GitHub/Claude review was independently verified. The historical fresh attestation and Stage6/7 reports were inspected and left unchanged. Those deployment/authority/isolation/review gaps remain denied by the existing Stage6 gate; existing Stage7 CEO proof/execute and durable reservation components are the source solution, subject to later approved runtime evidence. No gate override was added.

No real CEO, live inference, real capital/payment, deployment, restart, actual ledger access or Agents Manager/Worker change occurred. Existing signed state, keys and quota state were preserved by nonaccess; no independent live-state equality claim is made. P1-04 preserve-and-resume approval was recorded from the Owner's instruction and was not executed as part of this focused P1-03 task. Ambiguous outcomes remain held and existing no-duplicate inference checks pass.
