# P0.0 Infrastructure Boundary

## VM identities

| VM | Address | Role |
|---|---:|---|
| venture-control | 192.168.0.167 | Future control plane, policy kernel, broker, ledger, and supervisor |
| venture-agents | 192.168.0.116 | Agent runtime and worker plane |

- Reserved future broker API: venture-control:8443/tcp
- Administrator SSH source: 192.168.0.50

## P0.0 network invariant

The agent plane may reach venture-control only through the reserved broker API port, 8443/tcp. It must not reach control-plane SSH/22, bridge management ports, PostgreSQL/5432, Redis/6379, OPA administration, or any other control-plane service. There is no SSH or root path from venture-agents to venture-control.

The current UFW rules enforce the tested control-plane restrictions and permit the reserved 8443/tcp path from venture-agents. No service is listening on 8443 until the broker is implemented.

## Management-plane note

The ChatGPT2LocalBridge and Cloudflare tunnel are management-plane services and remain separate from the future broker API. The venture-agents host currently retains general outbound internet access because the bridge and tunnel require it. Workload-network isolation for agent processes remains a follow-up design item and must not be confused with broker authorization.

## External PostgreSQL backup

TrueNAS is available at 192.168.0.249. Its NFS export is mounted on venture-control at:

- Source: 192.168.0.249:/mnt/Data/epsilon
- Mount: /var/backups/venture-control
- Backup subdirectory: /var/backups/venture-control/venture-control

The backup service stages the pg_dump locally as postgres, then copies the completed dump to TrueNAS without requiring postgres to write directly to the NFS export. The current TrueNAS export is permitted to 192.168.0.0/24; narrowing it to 192.168.0.167 is a follow-up hardening action.

## Validation

The initial P0.0 validation confirmed:

- Both VM bridges are reachable and execute as epsilon.
- Noninteractive sudo is available through both bridges.
- Agents cannot reach control ports 22, 3838, 5432, 6379, or 8080.
- Control permits inbound 8443/tcp only from 192.168.0.116, pending broker implementation.
- PostgreSQL backup and restore completed successfully using the TrueNAS NFS mount.
