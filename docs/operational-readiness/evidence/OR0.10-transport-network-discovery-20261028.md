# OR-0.10 cross-VM transport discovery — 2026-10-28

**Gate: NOT ACCEPTED. No direct authenticated Control-to-Agents transport found or exercised.**

## Source findings
- `agents/ceo/provider_dispatch.py` invokes local manager `run_agents()`; `ventures/venture-001/runtime/provider_manager.py` launches local worker subprocesses. This path stays on Venture-Control.
- `agents/ceo/service_identity.py` already implements bounded Ed25519 service identities for CEO/manager/worker preparation attestations and excludes arbitrary signing; this should be reused for authorization envelopes instead of introducing an independent key hierarchy.
- `agents/ceo/authenticated_handoff.py` invokes local `self.control.dispatch` and persists a hash-recorded event; this is not a network transport.

## Network observations
- Venture-Control address observed on private network: `192.168.0.167`; Venture-Agents: `192.168.0.116`.
- SSH TCP/22 from Control to Agents failed with `Connection timed out` using batch mode and strict host-key checking. Reverse SSH from Agents to Control likewise timed out. **This only proves TCP/22 unavailable under these probes; it does not prove all transport is unavailable.**
- Both bridges/tunnels are active; Agents bridge runs a Node local bridge service and has loopback listeners at ports 20241 and 20242. These endpoints are **not an approved agent manager command API** and must not be repurposed for unrestricted operations or treated as signed handoff evidence.
- No firewall, SSH configuration, bridge, tunnel, external endpoint or service was altered.

## Implementation decision and gate
An authenticated transport requires an explicitly bounded receiver on Venture-Agents with a tested allowlist of test-only actions; an outbound-only securely authenticated path from Control using existing VM network or an approved tunnel; exact Ed25519 identity, audience, expiry, nonce/replay protection; signed acknowledgments; and negative tests for malformed/tampered/expired/replayed envelopes. Do not expose a generic remote shell or transfer owner/finance authority. Verify true VM-to-VM request delivery, not orchestrated bridge tool calls from ChatGPT.

**Blocking fact:** Existing active transports were not demonstrated to permit direct machine-to-machine, app-scoped dispatch. Before implementation, a scoped VM routing/binding choice is needed. No signed inter-VM transaction was performed, so OR-0.10 remains NOT ACCEPTED.
