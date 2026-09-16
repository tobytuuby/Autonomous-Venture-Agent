# ADR-003: Broker API authentication and internal execution

## Decision

The control broker is the only component that authorizes an execution request. An internal execution service retrieves a short-lived synthetic OpenBao lease, calls an allow-listed adapter, and returns a result envelope. Agent identities never receive the execution-service interface, an OpenBao token, or a raw credential.

OpenBao listens on loopback only. The agent VM reaches the broker, never OpenBao. The OpenBao policy grants only the internal service token the ability to mint a 60-second synthetic token; no agent policy grants any read or token-creation capability.

## Consequences

- Raw credentials remain in the execution-service call frame and are not serialized into agent results, logs, or job payloads.
- Leases are short-lived and non-renewable in the P0 synthetic provider.
- Real provider credentials are out of scope until a real integration is added behind this same boundary.
- The single-node file backend and loopback HTTP listener are a P0 deployment baseline; production requires TLS, durable off-box OpenBao backup, and an external unseal/key-management procedure.
