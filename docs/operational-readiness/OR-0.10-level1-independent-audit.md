# OR-0.10 Level 1 independent software audit — reproducibility contract

Status: **READY FOR INDEPENDENT AUDIT; NOT ACCEPTED**.

## Independent checkout (Claude)

Use a fresh checkout of `tobytuuby/Autonomous-Venture-Agent` on `main`. Record the full commit SHA and dirty/clean status. Do not rely on results from the Control VM. This audit is read-only and must not require VM access, production certificates, runtime secrets, or authority to approve a venture.

```bash
git clone git@github.com:tobytuuby/Autonomous-Venture-Agent.git
cd Autonomous-Venture-Agent
git checkout main
git rev-parse HEAD
git status --short
uv sync --project infrastructure/python-runtime --frozen
infrastructure/python-runtime/.venv/bin/python -m unittest discover -s tests -p 'test_cross_vm*.py' -v
```

A fresh environment might require `uv run --project infrastructure/python-runtime --frozen` for command execution; the explicitly selected interpreter above is used after `uv sync`. Execute from repository root for imports to resolve correctly.

## Existing deterministic suite

- `tests/test_cross_vm_transport.py`: signed assignment/acknowledgement validation, role/scope/expiry/replay errors, HTTP/TLS mock failures.
- `tests/test_cross_vm_state.py`: SQLite restart/replay/task reservation checks.
- `tests/test_cross_vm_outbox.py`: verified enqueue, conflicting assignments and restart behavior.
- `tests/test_cross_vm_poll.py`: simulated certificate-pin, URL and binding checks.

Baseline observed on Control workspace at short HEAD `b1bef41` on 2026-10-28: **28 tests, 0 failures**. This is operator-observed execution, **not** a substitute for Claude's independent run or review. The suite's fixture-based TLS tests **do not establish real mTLS issuance, client/server mutual authentication, rotation, cross-VM reachability, actual manager/worker execution, or signed execution evidence**.

## Independent audit deliverable

Record repository full SHA, interpreter/dependency versions, exact test command, exit code, raw sanitized test output, and explicit manual review findings. Review signature/key pinning, identity-role association, nonce/task concurrency and persistence, trust boundaries, exception handling, and insecure fallback. File each finding with severity, path/line, reproduction, and effect. Do not equate passing tests with absence of security defects.

## OR-0.10 gate boundary

**Level 1 PASS** requires the auditor's independent reproducible tests **and** completed code review with no unresolved blocking findings. A passing operator test run alone is `PENDING`.

**Level 2 PENDING** until separately authorized operational testing verifies a real encrypted Control ↔ Agents route, correct identities, real remote execution location, execution-bound signed evidence, negative tests and safe recovery. Signed `RECEIVED` acknowledgments alone are not evidence of execution. No owner approval, spending, payment, or venture-launch authority may be enabled by this audit.

Only the owner may accept the combined OR-0.10 gate after both levels have passed and evidence has been reviewed.
