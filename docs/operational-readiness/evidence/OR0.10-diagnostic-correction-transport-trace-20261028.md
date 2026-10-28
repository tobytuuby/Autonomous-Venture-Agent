# OR-0.10 bounded diagnostic correction and transport trace — 2026-10-28

**Verdict:** Local diagnostic instrumentation implemented; cross-VM signed transport NOT verified. OR-0.10 remains NOT ACCEPTED.

## Changes
- `agents/ceo/scheduled_exercise.py`: generic state-denied exception path now emits only allowlisted exception **type name** as `failure_category` in the sanitized status. Unknown subclasses map to `OTHER`. No exception values, payloads, credentials, tracebacks or paths are logged. Existing failed unit was NOT restarted; its original exception remains unknown until the next controlled execution.
- `agents/ceo/authenticated_handoff.py`: `dispatch()` calls `self.control.dispatch` and records local delivery state. This is not cross-VM transport.
- `agents/ceo/provider_dispatch.py`: dispatch instantiates local manager orchestration and calls `manager.run_agents()`. `ventures/venture-001/runtime/provider_manager.py` launches worker processes via `subprocess.Popen` in the current filesystem context. These inspected paths do not demonstrate transport to Venture-Agents.

## Focused tests
- `python3 -m unittest tests.test_scheduled_ceo_exercise -q`: 10 tests, PASS.
- `python3 -m unittest tests.test_authenticated_handoff tests.test_broker -q`: 30 tests, PASS.
- Initial test command incorrectly named nonexistent `tests.test_scheduled_exercise` and failed import; reran actual module `tests.test_scheduled_ceo_exercise`, PASS. No attempt was made to count the first failure as a passed test.

## Outstanding before acceptance
1. Controlled rerun of the advisory exercise by its authorized service identity to retrieve a new `failure_category`, after separate review; service left failed for now.
2. Identify and deploy an actual manager transport between Control and Agents; inspected local dispatch paths are insufficient. Do not assert SSH/TCP transport exists without evidence.
3. Only then perform an authenticated inter-VM request and acknowledged response using ephemeral test identities, and verify tampered and expired signatures fail closed. No owner/payment authorization enabled.

No sudo-driven service restart or live provider call; unrelated worktree modifications preserved.
