# OR-0.7.3 Python environment evidence — 2026-10-28

Status: **PASS bounded Python import checks on both VMs; independent audit pending**.

## Source-first requirement

Committed `infrastructure/python-runtime/pyproject.toml` and `uv.lock` before creating either environment, commit `4a87817bdf084c9d7e83088b56d009134aa534f3`, pushed to `origin/main`. `uv lock --check` passed with pinned uv 0.13.5 and `/usr/bin/python3` (Python 3.14.4). The lock resolved 16 total packages (14 installed Linux packages, including the root project's metadata), with 175 SHA-256 references. Lock SHA-256 on Control and Agents: `d5730dcba2ebb236cfa1e0d788af4493e9bf03f9192c9668b3237bbd03c40de5`.

## Execution results

| Host | Path | Interpreter | uv sync | Import tests | Result |
|---|---|---|---|---|---|
| venture-control | `infrastructure/python-runtime/.venv` | `/usr/bin/python3` 3.14.4 | `--locked --no-python-downloads --no-config` | cryptography,jsonschema,requests,psycopg | `CONTROL_PY_ENV_OK` PASS |
| venture-agents | `infrastructure/python-runtime/.venv` | `/usr/bin/python3` 3.14.4 | `--locked --no-python-downloads --no-config --no-install-package psycopg` | cryptography,jsonschema,requests | `PY_ENV_OK` PASS |

### Failure observed and corrected on Venture-Agents

The first sync on Agents attempted to install psycopg (declared in the shared lock) and its import failed because the agent host lacks libpq. This **was not successful acceptance** and exposed an over-broad shared manifest for Agents. No system libpq or PostgreSQL packages were installed. Corrected by re-syncing with `--no-install-package psycopg`, then verified `PSYCOPG_PRESENT False` and `PY_ENV_OK` for the three actual shared imports. For future reproducibility, the agent runtime deployment must encode the `--no-install-package psycopg` override or split its dependency definition in a separately approved task. Do not claim `uv sync --locked` alone succeeds for all required imports on Agents.

No sudo, modifications to system Python, or service restart. Existing unrelated worktree changes preserved.

**Scope:** Only locked runtime dependency installation/import proof; no end-to-end CEO, manager, worker, browser, or finance certification.
