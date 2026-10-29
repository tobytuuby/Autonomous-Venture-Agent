# Level 2D mTLS renewal: live operational acceptance evidence

Date: 2026-10-29 UTC. Operator implementation, not independent Claude audit.

- OpenBao CA retained. Renewed CEO, Manager and broker leaf certificates with existing identities, without exporting private keys or giving Agents an OpenBao signing token.
- Broker SAN verified: DNS venture-control, DNS localhost, IP 192.168.0.167. An initial missing-SAN broker certificate was rolled back immediately, reissued with SAN, and retested.
- Scopely restricted OpenBao token installed root-only under /etc/venture-control/level2d-renewal.token. Only three PKI sign paths and self-renew/lookup are allowed by level2d-pki-renewal policy. CA private key and root token are not staged or committed.
- Authenticated Manager CSR POST over the existing private mTLS broker returned HTTP 200. Control root renewal service signed the CSR, updated the Manager certificate pin, and broker restarted successfully.
- Manager downloaded the cert from the broker, checked the CA and public key against the unchanged local private key, atomically installed it, and restarted successfully. Manager mTLS poll returned HTTP 200.
- Control timer venture-level2d-cert-renew-control.timer enabled and active, daily at 03:30 UTC. Agents timer venture-level2d-cert-renew-agent.timer enabled and active, hourly. Manual service executions both returned Result=success.
- Current renewed expiry times: Manager 2026-11-12T14:13:47Z, CEO 2026-11-12T14:01:47Z, broker 2026-11-12T14:04:41Z. These 14-day certificates need active renewal timers; a timer failure must be monitored prior to expiration.
- Certificate renewal scopes are outside business, deployment, finance, and Worker operating authority. Existing Level 2C signed assignment and Manager polling services remain operational.
- Synthetic unit tests for bounded CSR and tampering: 16/16 focused tests. Control full regression with renewal endpoints: 976/976 passed.
- Remaining nuance: certificate rotation keeps the existing private keys. Public/private key replacement after compromise requires separate explicit revocation and provisioning; this flow performs ordinary leaf certificate renewal only.
