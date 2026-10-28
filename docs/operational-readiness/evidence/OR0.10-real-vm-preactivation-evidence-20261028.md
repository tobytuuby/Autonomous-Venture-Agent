# OR-0.10 Level 2B — Real-VM verification and activation blocker (2026-10-28)

## Scope
Owner requests real Control/Agents signed assignment, mTLS and negative-authentication evidence, reviewed by Claude before acceptance. These checks were performed **without** restarting services, changing ports, issuing production credentials, delivering assignments, or granting execution authority.

## Results actually observed

- Control VM at `1e50dae5f265526d2c64a569a84ab6cc21c2c391`; `venture-control-broker.service` active.
- Control `ss -ltn` reports broker bound to `0.0.0.0:8443`. Deployed `/usr/local/lib/venture-control-broker/kernel/broker/server.py` and its unit launch Python `ThreadingHTTPServer` **without TLS wrapping**. The production broker is therefore plaintext, not mTLS.
- Agents VM has protocol files and test modules; `ss -ltn` shows no active Agents mTLS protocol listener.
- Control cross-VM deterministic tests: **28/28 PASS**, command `infrastructure/python-runtime/.venv/bin/python -m unittest discover -s tests -p 'test_cross_vm*.py' -q`.
- Agents cross-VM deterministic tests: **28/28 PASS**, command `python3 -m unittest discover -s tests -p 'test_cross_vm*.py' -q`.
- Control synthetic TLS integration tests: **15/15 PASS**, command `infrastructure/python-runtime/.venv/bin/python -m unittest tests.test_broker_isolated_mtls -q`. Earlier combined 27/27 includes these 15 + 12 broker tests.
- A static search of configured services, local bin and cron locations on each VM found no additional literal references to `8443`/`capabilities/evaluate` (not proof of exhaustive clients).
- No live signed delivery nor CEO/manager acknowledgement across the two VMs occurred, and no live role-boundary/9-authorities check was executed in this session.

## Correct acceptance status

**NOT ACCEPTED.** A real-VM mTLS handshake with assignment receipt is not possible against the current plaintext listener. Tests validating individual modules and isolated TLS do not prove real VM delivery. Claude's acceptance is needed for production transport activation. There is no basis to call this completed security gate.

## Minimal next implementation

1. Prepare a production-ready broker entrypoint based on `kernel/broker/isolated_mtls.py` preserving only existing capability routes plus read-only signed-assignment polling, with identity-specific authorization and no execution.
2. Configure distinct service identities, server trust and pinset using existing OpenBao facilities. Do not put private keys in the repository or evidence.
3. Obtain Claude's review of changed files and activation configuration, then apply approved **planned-downtime** broker switch on existing TCP/8443. If activation fails leave broker stopped, never revert to plaintext.
4. From Agents, execute real HTTPS + signed polling; verify signature and manager receipt/acknowledgment (without dispatching work). Reject missing/wrong/expired cert, wrong role, plaintext, and forbidden capability requests; verify all nine prohibited live authorities.
5. Record sanitized service hashes, listener and negative/positive evidence and submit for Level 2B acceptance.

This record contains no production secret and certifies only the checks explicitly executed above.
