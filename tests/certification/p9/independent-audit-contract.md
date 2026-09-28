# P9 Independent Audit Contract

**Audit state:** Pending; no P9 acceptance is claimed.

The reviewer must be independent of implementation and must use the full commit and original repository artifacts, not this summary alone.

## Reproduction

From the repository root, run and record UTC timestamp, Python version, exact exit code, and complete output:

- `PYTHONPATH=. python3 -m unittest tests.p9.test_p9_synthetic_boundary -v` — expected 48/48.
- `PYTHONPATH=. python3 -m unittest discover -s tests/p8 -p 'test*.py' -v` — expected 59/59.
- `PYTHONPATH=. python3 -m unittest discover -s tests -p 'test*.py' -v` — expected 501/501.
- `git diff --check`.

## Source and boundary review

1. Verify the source commit descends from P8.4 merge `0f8df0f00f15207afdf7bfe74bb466aa3d6dd386`.
2. Recompute every SHA-256 and byte length in `manifest.json` and `source-inventory.json`.
3. Confirm all nine fields in `kernel.p6.registry.LIVE_FIELDS` are required false on input and hard-coded false on every output.
4. Trace all imports and call paths in `kernel/p9`; confirm no network, subprocess, credential, filesystem, provider, deployment, worker, venture, or external-action capability exists.
5. Inspect charter binding, event identity, sequence, cross-venture/portfolio isolation, model-output handling, canonical hashing, failure stop, recovery terminal states, and schema validation against policy.
6. Verify each of the 48 named cases is independently discoverable, maps to the focused raw log, and asserts the stated outcome. Confirm the 59 P8 and 501 full-suite denominators from raw logs.
7. Confirm no real CEO, live worker/venture authority, live authority bit, customer/capital/payment/broker/deployment/network/credential/provider action, or P10 work is enabled or performed.

## Decision record

Record reviewer identity and non-implementer declaration, commit reviewed, commands and environment, recomputed hashes, case and denominator results, source/call-path findings, limitations, and ACCEPTED or BLOCKED. Any unexplained mismatch or boundary weakness blocks acceptance. This audit can certify synthetic behavior only; it cannot authorize production, live operation, authority expansion, or P10.
