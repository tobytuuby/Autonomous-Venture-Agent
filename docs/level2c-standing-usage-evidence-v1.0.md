# Level2C standing inference policy v1.0 — 2026-10-28

Scoped replacement of the preparation exchange's per-workflow signed inference grant. No broker, launch, finance, service installation or operational authority change.

The entrypoint no longer reads `inference_grant` or `operator_public_key`. It requires an operator-owned mode-0600 `exchange-usage-policy.json` in the existing fixed `service_identity.AUTHORITY_DIRECTORY` (normally `artifacts/preparation-authority`). No default usage policy is created. Schema:

```json
{
  "domain": "preparation-exchange-usage-v1",
  "enabled": true,
  "epoch": 1,
  "roles": {
    "ceo": {"actor_id": "ceo", "endpoint": "https://operator-configured.example/v1", "model": "gpt-6-sol"},
    "manager": {"actor_id": "manager", "endpoint": "https://operator-configured.example/v1", "model": "gpt-6-sol"}
  },
  "maximum_requests": 8,
  "maximum_output_tokens": 1024
}
```

Actor IDs must match the trusted workflow context; each provider must match its exact endpoint/model pin. Epoch must match central authority. Limits may only narrow the hard maxima shown. The request ceiling covers the entire session across both roles, across days and state directories. The existing shared daily ceilings remain 94 requests and 1,540,096 reserved output tokens; this exchange still caps each response at 1,024 tokens. Models cannot select policies, quota stores or tools.

Local FULL-synchronous SQLite intent commits before central session reservation, then existing `ServiceIdentities.reserve_provider` reserves daily usage before transport. Central `exchange_sessions` and `exchange_calls` tables live alongside existing reservations in `resources.sqlite`; atomic session counting and unique logical-call identities prevent directory changes, concurrency or policy replacement from renewing a session. Context/policy changes hold existing sessions. Failures may conservatively burn session capacity before a daily reservation exists; neither provider ambiguity nor response-checkpoint failure refunds daily capacity. Exact successful local replay reads cached JSON without another provider call. Legacy grant rows cannot replay under the standing binding and require operator reconciliation; no automatic migration or reset is provided.

Validation uses synthetic in-process providers, ephemeral identities and loopback TLS. Tests cover the grant-free CLI, both-role quotas, daily request/token exhaustion, concurrent session reservations, restart and directory-change replay denial, a crash between session and daily reservation, response-checkpoint failure, changed requests/providers/roles, missing/insecure/disabled/changed policies, revocation, tool denial and invalid JSON.

Validation on the final source (all commands run with `TMPDIR="$PWD/artifacts"`):

```sh
infrastructure/python-runtime/.venv/bin/python -B -m unittest tests.test_preparation_exchange tests.test_agent_identity tests.test_cross_vm_outbox tests.test_cross_vm_poll tests.test_cross_vm_state tests.test_cross_vm_transport tests.test_provider_dispatch_transport -v
# Ran 64 tests in 15.828s; OK
infrastructure/python-runtime/.venv/bin/python -B -m unittest discover -s tests -v
# Ran 929 tests in 60.037s; OK
git diff --check
# exit 0
```

Both asynchronous processes were polled to exited and completed raw logs read through venture-control. Focused process `proc_mvslxdsv_ohm554` (PID 2335132), regression `proc_mvslxikx_xbp7py` (PID 2335204). Raw per-test decision logs retained locally in ignored artifacts:

| Log | SHA-256 |
| --- | --- |
| `artifacts/level2c-focused-final.log` | `75b770f8e8f629c8f7eac675bf999f0b09771217b4b3f7977562002b522971c4` |
| `artifacts/level2c-regression-final.log` | `720f55cf754d4707783510367dca61104ac83db2f4ec57055a575fbfed341d39` |

Earlier iterations also passed: 17 exchange tests, then 926 regression tests. Three additional failure/concurrency/CLI tests and stricter peer actor binding prompted the final runs above. No failing test result was hidden. These logs require workspace access; this concise document is not a substitute for raw scenario evidence or independent certification.

Assessment: code/test evidence supports the bounded standing-policy implementation. No production policy was installed or live exchange run. Reservations are ceilings and attempted-call evidence, not measured token consumption, invoices or verified monetary spend. Existing provider traces remain redacted protocol evidence; real provider execution/reachability and actual cost are unverified. One shared authoritative store is required: independent VM-local copies do not constitute a distributed global quota. Protect and retain that ledger; operator deletion/rollback is outside the process crash/restart guarantee. Independent GitHub/Claude review remains pending; this document does not accept OR-0 or authorize operations. ADV-001–ADV-049 and /49 remain unchanged. No real CEO, capital/payment, launch or deployment action was used. Unrelated dirty files were excluded from this change.
