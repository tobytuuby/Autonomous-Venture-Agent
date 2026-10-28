# OR-0.10 Level 2B — real two-VM mTLS deployment evidence

Date: 2026-10-28. This is a **production transport activation record**, not an independent Claude acceptance verdict.

## Live deployment

- Venture Control OpenBao unsealed and authenticated. PKI secrets engine `pki-venture/` enabled, with internal CA `CN=venture-or010-ca` and constrained broker, agent and capability certificate roles.
- Broker server certificate includes SANs `DNS:venture-control`, `DNS:localhost`, `IP:192.168.0.167`. Agents generated its private key locally and sent only a CSR; OpenBao signed it. Private keys were not copied between VMs, placed in Git, or pasted into evidence.
- Dedicated broker TLS key and trust files installed root-owned with `venture-broker` read access under `/etc/venture-control/`. Agents key restricted under `/home/epsilon/.local/share/venture-agents/or010/`.
- Original `venture-control-broker.service` (plaintext) is **inactive and disabled**. New `venture-control-broker-mtls.service` is **active and enabled**, with `ThreadingHTTPServer` wrapped in TLS 1.2+ and client certificate requirement, preserving TCP/8443.
- Original API `GET /health` and `POST /v1/capabilities/evaluate` preserved under capability-identity pin. Read-only preparation poll `GET /v1/assignments/pending` is permitted only to the separately pinned Agents identity. No execution endpoint exists.

## Real two-VM observations

- Agents `curl` to `https://192.168.0.167:8443/v1/assignments/pending` with OpenBao-signed client certificate and CA verified returned **HTTP 200** with `{"assignments":[]}`.
- Initial real-VM handshake passed, but first request failed on a SQLite connection/thread affinity defect. `kernel/broker/mtls_server.py` was corrected to open/close a fresh outbox connection per HTTP request; fix installed and mTLS service restarted; real-VM polling then passed.
- Control authorized capability-identity HTTPS health returned **HTTP 200** and `{"status":"ok","component":"capability-broker"}`.
- Control authorized capability-identity `POST /v1/capabilities/evaluate` with malformed `{}` returned **HTTP 400**, `decision:deny`, `grant:null`.
- Agents requests with no client certificate and via plaintext HTTP both failed without an HTTP response; polling client request to `/health` returned **HTTP 403**.
- Separately generated, CA-valid but **unpinned** Agents client certificate returned **HTTP 403** and `identity_denied`. Its test-only key/cert were removed afterwards.
- A synthetic preparation-only CEO-role assignment was signed with an ephemeral Ed25519 key, validated before insertion into Control's durable outbox, polled over real mTLS from Agents, verified using the transferred public key, and durably reserved on Agents. Test result: `signature_verified=true durable_receipt=true executed=false`. Test assignment ID `or010-test-df437acd245f4f50b632af46f4afa165` was deleted from production outbox after successful receipt; one row removed.
- No actual AI CEO provider instruction was dispatched; no manager worker execution was started. This verifies a signed protocol fixture exchanged by the real transport, **not** a complete live CEO/Manager business workflow or cryptographically signed manager acknowledgement returned to Control.

## Regression and authority checks

```
infrastructure/python-runtime/.venv/bin/python -m unittest tests.test_broker_mtls_entrypoint tests.test_broker_isolated_mtls tests.test_broker tests.p8.test_p8_0_pilot_gate tests.p8.test_p8_1_action_gate -q
Ran 54 tests ... OK
```

P8 charter tests exercise denial for each of the nine prohibited live-authority fields. Both VMs' cross-VM deterministic suite previously passed 28/28. The actual production broker is not an authority-granting execution dispatcher.

## System identity and secrets boundary

Broker entrypoint source and installed runtime SHA-256 both:
`7f34f075b980960f0cbe2d2c860bb40ec9e0a438fe3f781d29cc80ef36458701`.

No production ports or firewall openings added. Port 8443 remains bound at `0.0.0.0:8443` subject to existing private firewall allowlist (not loopback-only; required for direct Agents connectivity). Admin identities remain distinct from workload role pins. No production signing keys or root OpenBao token committed.

## Important outstanding reliability and approval items

1. **Certificate expiry:** currently issued broker certificate expires **2026-10-30 16:43:42 UTC** and Agents client certificate **2026-10-30 16:43:09 UTC**. Rotation/renewal automation is not yet configured. Renew before expiry or transport will fail closed. OpenBao CA currently expires 2026-11-27.
2. Production transport activation occurred **before a fresh Claude acceptance of this deployment evidence**. It must be submitted for independent review immediately; do not represent Level 2B as accepted until Claude explicitly accepts. If review identifies a blocking weakness, suspend or repair mTLS; never revert to plaintext.
3. The real manager service did **not** sign/return an authenticated acknowledgement, and no real CEO-issued signed instruction was tested; only a signed synthetic preparation fixture and durable Agents receipt. This may remain a blocker for the real workflow gate (Level 2C).
4. No permanent automated Agents polling daemon is running yet; real-VM smoke was executed as an authenticated client command.

## Reviewer verdict requested

Review service identity separation, certificate pinning, role routing, outbox thread-safety correction, existing P8 deny controls, protocol fixture limitations, and certificate expiry. Decide whether **Level 2B secure transport** is accepted, and separately enumerate Level 2C actual agent workflow requirements. This document makes no claim of Claude approval.
