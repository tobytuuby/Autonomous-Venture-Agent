# Bounded Worker reservation diagnosis — evidence pending

Inspected HEAD: `a3522995ccb38bd40d369a9cf28323313743254e`, branch `main`.
Target supplied by owner: `level2d-multiworker-remediation-1`, WORKER_PENDING revision 5; Worker a/b reservation HTTP 400, target central reservation count zero. These current runtime facts are owner-reported, not independently confirmed in this inspection.

## Confirmed source behavior

- `kernel/broker/isolated_mtls.py` maps reservation validation ValueError, TypeError, KeyError, UnicodeError and RecursionError to HTTP 400 with `{"error":"worker_inference_denied"}`. `HierarchyClient` reports `broker hierarchy request failed with HTTP 400` without the response body. Neither message identifies the underlying validation failure.
- `worker_inference.authorized` requires exact reservation fields including assignment_id, matching authenticated Worker identity, valid digests, an allowed Control policy equal to the submitted policy, current authority epoch/no revocation, signed ready assignment and exact authoritative snapshot digest. These checks precede reservation accounting. Quota checks can also raise ValueError and produce the same HTTP response.
- `valid_policy` permits only enrolled worker-a/b/c, at most three distinct actors. A historical four-actor policy including service-worker fails with `bounded worker actors required`; an otherwise valid differing submitted policy fails with `changed worker policy`. Neither is established as the current runtime error.
- `HierarchyProvider` commits `(identity, canonical request, NULL response, attempt)` locally before calling worker_reserve. Failure leaves that intent unresolved. A subsequent Worker call with the same request raises `ambiguous provider call requires reconciliation` before another reservation or execution request. This is a deliberate fail-closed boundary.
- The adapter does not persist the submitted reservation policy alongside that local intent. The exact originally submitted policy therefore requires contemporaneous configuration/evidence; today's policy alone cannot prove it.

## Evidence and decision

No current rev5 snapshot, current Control/Agents policy pair, or current per-intent execution evidence was available in the inspected in-root files. The available observation JSON predates rev5. Historical activation policy contains four actors while the checkout's active policy template contains three. Templates and old observations do not prove current configuration or loaded code.

The owner restricted work to the approved project root. Installed runtime paths referenced by older inspection scripts lie outside that root; those scripts were not executed. No runtime endpoint, provider, signer, privileged command, restart or ledger mutation was invoked.

Decision: exact runtime cause UNVERIFIED; no speculative implementation or configuration change. Do not deploy or reconcile on the basis of this report. Existing signed ledger, local intents, historical evidence, limits and unrelated worktree changes are preserved. No refunds. ADV universe and /49 unchanged.

## Required next evidence and safe correction sequence

1. An authorized operator should stage sanitized, timestamped read-only evidence inside this project: current Control and Worker a/b policy JSON; installed module hashes/process start identity; cryptographically verified target workflow revision and snapshot hash; authenticated actor/assignment mapping; and each unresolved local identity, attempt and request hash (exclude prompts, private keys, tokens and secret environment values).
2. With callers quiesced by an authorized operator, prove centrally in a consistent read-only snapshot that each exact reservation key is absent from worker_reservations AND worker_executions AND the daily reservations ledger. Compute the key exactly as digest(canonical({domain: worker-budget-key-v1, workflow_id, assignment_id, identity})). Also check all target-workflow records, not only one guessed key. Correlate provider dispatch/trace evidence and establish no provider execution for these attempts. A zero reservation count alone is insufficient; missing logs or snapshots are not proof. Stop if evidence is incomplete or inconsistent.
3. Reproduce the precise failing validation offline using staged evidence and the verified deployed validator, without calling reserve_worker, execute_worker, provider or signers against live state. Fix only that proven contract/configuration mismatch, retaining actor restrictions, signed state, caps, historical minima and daily accounting. Run a targeted regression reproducing it, focused boundary tests and git diff --check. Review the exact diff before separately authorized deployment.
4. Any later deployment must keep inference callers quiesced and paid/provider dispatch disabled, preserve database/configuration backups and hashes, install only reviewed changed components/configuration, and verify installed hashes and policy equality before restarting authorized services. A service restart may automatically dispatch inference; it must not occur under this task's no-paid-calls restriction.
5. No exact local-intent reconciliation is authorized or supplied here because absence and non-execution have not been proved. Do not DELETE/UPDATE calls, create a fresh identity/attempt, reset state, use the Manager research reconciliation override for Workers, or replay the adapter into live endpoints. Preserve the original identity/request/attempt and unresolved row. A future narrowly reviewed reconciliation must bind the proven evidence to that exact intent, revalidate unchanged signed state/assignment and current policy, retain all charges, and handle duplicate reservations safely. Any execution after reconciliation requires separate authorization; the current adapter rejects a duplicate reservation receipt and is not an automatic recovery mechanism.

## Validation

Command:

```sh
infrastructure/python-runtime/.venv/bin/python -B -m unittest tests.test_worker_inference tests.test_hierarchy_providers tests.test_hierarchy_multi_worker tests.test_broker_isolated_mtls -v
```

Result: 57 tests passed, 11.294 seconds, exit 0. Raw output: `artifacts/worker-reservation-diagnosis-focused.log`; exit: `artifacts/worker-reservation-diagnosis-focused.exit`. Bridge process `proc_mvwqgv0l_41jd91`, PID 1321190, observed exited before reading the completed in-project log. Tests use local fixtures/fake providers and do not prove live acceptance. `git diff --check` passed before this report was added; final check recorded in the task response.

Changed by this task: this report and the two ignored test-output artifacts above. No implementation or test-source changes. No commit, push, deployment, production CEO, capital, payment or venture-launch action.
