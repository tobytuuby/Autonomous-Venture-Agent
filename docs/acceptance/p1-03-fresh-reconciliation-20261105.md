# P1-03 fresh installed-runtime dependency reconciliation

Decision: P1-03 dependency reconciliation is complete for isolated synthetic compatibility. No deployment or production acceptance is authorized. No architecture, authority invariant or phase requirement changed.

The requested baseline be2feea is an ancestor of observed main ef154cdf1f5ea0abedf63520fa8f934f37fa2511. The intervening 7638e0b already fixed the isolated fixture dependency closure. Its evidence and all unrelated untracked work, including the original ceo-attestation-20261105 directory and P1-04 files, were preserved. This follow-up replaces dependence on historical snapshot availability with a declarative manifest and repeatable fresh read-only Python-source snapshot workflow. All commands used venture-control; all writes remain under the project root.

## Exact two errors and retained minimal fix

Both CEOCandidateAcceptanceTests methods failed before their bodies:

- test_three_round_process_exit_recovery_preserves_signed_trace_and_quota
- test_two_created_synthetic_ventures_reject_cross_bound_reservation

In inherited ResearchMtlsAcceptanceTests.setUp, patch resolution for kernel.finance.finance.FinancialGovernor.allocate imports kernel.finance.__init__, then payment_path, then integrations.payment_adapter. The installed CEO tree lacks integrations. pkgutil.resolve_name catches the strict finder's ImportError and reports AttributeError: module 'kernel' has no attribute 'finance'. Fresh before-fixture evidence reproduces exactly 17 tests with two errors and two denied integrations imports, matching the untouched original attestation.

The fix is exclusively fixture packaging of existing integrations/payment_adapter/{__init__,real,simulated}.py. Those three files provide transitive imports and external-operation denial patch targets. The denial patches remain intact. No production install manifest needs changing for this test-only dependency. No payment adapter is invoked. The strict finder never substitutes repository files for missing installed files.

## Fresh compatibility manifest and tests

infrastructure/ceo-installed-compatibility.json names the two actual installed roots, eight pre-existing Stage7 source overlays, three fixture-only dependencies, and exact test profiles. scripts/ceo_fresh_installed_compatibility.py reads public .py files only from installed agents/kernel/integrations and checks broker ActiveState through systemctl show. It never imports installed code directly, reads credentials or ledger/configuration files, or mutates services. All test execution uses new project-contained snapshots. Candidate overlays are explicit committed source bytes, verified against the checkout. Every protected module load has a raw import SHA-256 checked against its selected profile. Missing modules fail closed even when checkout files exist; the regression now covers both CEO and broker profiles, six isolated negative-import cases.

The fresh source-installed-matrix.json records every installed Python file plus explicit additions: CEO 126 installed files / 130 matrix rows; broker 123 installed files / 128 matrix rows. It records source, installed and candidate hashes, origin, and observed test profile per row. These are compatibility candidates, not a blanket replacement of installed code with current main. Other installed/source differences are retained explicitly, not silently synchronized. The three adapter files are fixture-only and must not be interpreted as a production deployment instruction.

## Independently observed validation

Evidence directory: tests/acceptance-evidence/p1-03-fresh-reconciliation-20261105/.

| Check | Exact result |
| --- | --- |
| Fresh candidate before fixture packaging | 17 tests; expected two setup errors; exit 1 |
| Strict candidate CEO pending recovery / candidate acceptance | 17/17; zero failures/errors; exit 0 |
| Strict installed broker mTLS | 20/20; zero failures/errors; exit 0 |
| Strict candidate CEO broker route | 12/12; zero failures/errors; exit 0 |
| Strict candidate broker mTLS / startup gates | 30/30; zero failures/errors; exit 0 |
| Source fallback / Stage6 denial / pending recovery / candidate regression | 20/20; zero failures/errors; exit 0 |
| Installed disk bytes before/after | Identical in both protected Python trees |
| Broker service metadata | ActiveState=active |
| git diff --check and staged check | exit 0 |

Raw per-test logs, commands, exits and import records are retained, including the intentional before-fixture failure. Candidate CEO logs contain expected ERROR-level messages from injected transport failures; unittest reports zero errors. Denied integrations.payment_adapter.RealPaymentAdapter submodule probes are pkgutil's attribute-resolution probes; the exported class resolves successfully. No real missing dependency was ignored.

Fresh validation process: proc_mw34jdkq_09r3kh, PID 3723326; regression: proc_mw34kx8m_he92a2, PID 3752036. Both started asynchronously, were polled to exited, and their completed project logs and exit files were read through venture-control. Bridge process log paths are recorded in processes.json. Intermittent bridge internal/connection errors were retried; a failed start produced no process or project log and was not counted as an execution.

To reproduce, use a new output directory:

    python3 -B scripts/ceo_fresh_installed_compatibility.py tests/acceptance-evidence/p1-03-fresh-NEW

A pre-existing output or snapshot is rejected. The regression command is in regression-command.json. SHA256SUMS covers raw evidence and source.sha256 pins the changed implementation, manifest and regression test.

## Authority, limitations and review decision

Classification: fresh installed disk snapshot plus explicit existing source/fixture overlays, exercised with synthetic providers, signers and ledgers and real loopback TLS. Disk snapshots were independently read and matched again after execution. Loaded production bytecode, provider execution, pending live work, live ledger equality, production process isolation and GitHub/Claude review are not attested by this task. The ADV-001–ADV-049 universe and /49 denominator are unchanged; these results are supplemental.

Review decision: accept P1-03 fixture dependency reconciliation and isolated compatibility only. Existing deployment and safety gates remain binding and denied where unsatisfied. Owner-confirmed preserve-and-resume, inference deduplication and ambiguous-outcome holds were not modified; existing synthetic checks pass. Signed live state was preserved by nonaccess, not by a claimed live-state audit. No owner action is required to close this scoped compatibility task. Later deployment requires its existing gates and separate authority.

No production service, live ledger, venture state, Agents Manager or Worker changed. No real CEO, provider inference, capital/payment, launch, deployment or restart was used. Phase 1 is not deployed by this work.
