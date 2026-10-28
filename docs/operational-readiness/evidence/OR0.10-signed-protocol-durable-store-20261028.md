# OR-0.10 implementation increment: signed protocol and durable reservations (2026-10-28)

**Status: PARTIAL. OR-0.10 still NOT ACCEPTED.**

## Implemented
- Committed previously present but untracked `agents/ceo/cross_vm_transport.py` (HTTPS-only explicitly addressed sender, pinned Ed25519 actor-role validation, bounded validity window, nonce/replay callbacks, acknowledgment signature/binding checks, no redirect and no automatic retry after ambiguous delivery).
- Repaired Python fixture booleans in its existing untracked protocol tests and committed the tests; 19 deterministic cases passed.
- Added `agents/ceo/cross_vm_state.py` durable SQLite nonce consumption and task ID reservation: atomic `BEGIN IMMEDIATE`, unique constraints and durable `FULL` synchronous mode; no automatic release/retry; conflict is denied.
- Added `tests/test_cross_vm_state.py`, validating duplicate rejection, persistence across reopen, conflicting digest, and fail-closed invalid inputs.
- Combined focused run: 39 tests passed (`cross_vm_state`, `cross_vm_transport`, `authenticated_handoff`); broader prior run 49 passed (`cross_vm_transport`, `authenticated_handoff`, `broker`).

## Actual connectivity
- Control -> Agents TCP/22 and TCP/8443 tested unreachable (timeout). Agents -> Control TCP/8443 reachable but HTTPS negotiation fails (existing broker is not TLS). This is not an authorized channel for transferring private instructions. Neither bridge sessions nor isolated tool calls count as inter-VM agent transport.

## Missing, non-negotiable
- No live TLS receiver on Agents, no verified trusted provisioning of manager signing key and CEO public trust pins on Agents, no broker/OPA authorization at receiver, no actual manager-worker execution on Agents, no signed round trip between VMs, and no network interruption recovery demonstrated. Existing owner approval and financial boundaries unchanged.
- Do not expose a generic remote shell, reuse HTTP broker plaintext as a secure channel, or infer successful integration from local synthetic tests.

## Next implementation gate
Choose and verify a restricted encrypted connectivity route (outbound Agents polling a verified Control HTTPS endpoint is plausible when Control -> Agents is blocked), then deploy a dedicated authenticated receiver bound to verified role/scope and OPA policy, and test a genuinely inter-VM round trip using test-only keys, denial, idempotency and interruption.
