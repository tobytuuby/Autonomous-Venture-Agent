# OR-0.10 Level 2B — Owner scope approval and isolated compatibility baseline

Date: 2026-10-28
Decision: **OWNER APPROVED** the Option A v0.1 policy amendment for **isolated preparation and compatibility testing only**, as stated in the conversation.
Reference: `docs/operational-readiness/OR0.10-broker-mtls-option-a-policy-v0.1-DRAFT.md`.
This record acknowledges the owner's approval; the draft remains a versioned source of requirements. It is **not** authorization for production certificates, broker cutover, firewall adjustment, work dispatch, or finances.

## Current observed baseline

Control repository `main` at `720ee3ef12ba5b27ec295e395483e3f7ab823f4f`. Existing unrelated dirty/untracked files preserved.

- Running `venture-control-broker.service` active as `venture-broker`, using `/usr/bin/python3 /usr/local/lib/venture-control-broker/kernel/broker/server.py`.
- Port `0.0.0.0:8443` is a plaintext Python HTTP listener: TLS/mTLS **not** active.
- Broker source serves `GET /health` and `POST /v1/capabilities/evaluate`; polling route does not exist.
- Repository search of Python/service files in `agents/`, `kernel/`, `infrastructure/`, `tests/` found no hardcoded URL clients for `http(s)://...:8443` and no references to `capabilities/evaluate` beyond the broker handler. **This is not a complete runtime caller inventory:** deployed unit drop-ins, external scripts, processes and monitoring must be checked separately prior to cutover.
- Deterministic baseline: `infrastructure/python-runtime/.venv/bin/python -m unittest tests.test_broker -v` → **12 tests, 0 errors/failures**, exit 0. This validates broker policy methods, not end-to-end HTTP compatibility.

## Remaining isolated work and gates

1. Complete actual running-client inventory and explicitly distinguish known clients, unknown clients and migration owners.
2. Create isolated test-only transport harness with fixture certificates/identities; do not reuse production secrets or issue production certificates.
3. Verify mutual TLS positive and negative cases, exact path/method identity authorization and no downgrade.
4. Capture existing route HTTP response compatibility from isolated tests using the old handler, then assert the upgraded handler's behavior is identical for authorized clients and denies unauthorized clients.
5. Check OPA-denied and malformed POST cases, callback behavior and certificate rollover/recovery in isolation.
6. Submit test evidence, client migration plan and safe cutover/rollback for separate owner authorization.

**Current disposition:** isolated preparation approved; compatibility baseline passed; production mTLS and OR-0.10 Level 2B certification **PENDING**.
