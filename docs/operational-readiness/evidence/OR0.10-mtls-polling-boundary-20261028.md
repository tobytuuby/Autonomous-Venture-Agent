# OR-0.10 mTLS polling component evidence (2026-10-28)

Status: **BOUNDARY CODE PASS / NOT DEPLOYED / OR-0.10 NOT ACCEPTED**.

- Added `agents/ceo/cross_vm_poll_server.py`: dedicated read-only `/v1/assignments/pending`, rejects non-TLS requests and unpinned client certificate, requires TLS `CERT_REQUIRED` with configured client CA, binds only to loopback behind separately approved route. No arbitrary shell, execution, key provisioning, or finance operation.
- Added `agents/ceo/cross_vm_poll_client.py`: exact HTTPS endpoint path, TLS server trust and client certificate, bounded response, verifies each assignment using existing Ed25519 and nonce callback before returning it to a caller. Does not execute work or authenticate an execution result.
- Ran `infrastructure/python-runtime/.venv/bin/python -m unittest tests.test_cross_vm_poll tests.test_cross_vm_outbox tests.test_cross_vm_transport tests.test_cross_vm_state -q`: **28 tests, PASS**. These are deterministic local tests; actual mTLS handshake/network or host-to-host request not tested.
- No service installed or restarted; no certificates issued or shared; no tunnel/firewall changes; no owner/financial authority changed. Unrelated worktree edits preserved.

**Gaps:** provision and independently validate scoped mTLS identity, approve tunnel or LAN transport, integrate existing broker/OPA policy at receiver, resolve threading and durable consumption/ack reconciliation, implement restricted Agents manager/worker execution, signed completion evidence and denial/replay/interruption end-to-end tests. Avoid treating a signed receipt as proof of execution.
