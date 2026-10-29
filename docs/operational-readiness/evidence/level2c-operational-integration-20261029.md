# Level 2C — bounded production-transport integration evidence
Date (UTC): 2026-10-29. Status: PARTIAL — no Level 2C operational acceptance claimed.

## Code under verification
- Source commit: `3fbff163d86c3b285e9d974a7da0ff2dda36f3d7`.
- Broker-mediated CEO assignment submission and CEO-only status implemented with mTLS certificate pinning. Manager-only polling and acknowledgement remain separately scoped.
- Provider reservations use Control-owned, mode-0600 central SQLite, operator standing policy, and role-bounded session binding. No plaintext or local-Agent quota fallback.
- Control full regression: 956/956 passed after signed ingress integration.
- Agents full regression: 365/365 passed after installing `psycopg==3.3.2` and OS `libpq5`.

## Live two-VM transport checks (not an AI journey)
- Control's mTLS broker actively serves 8443, with a staged full-module runtime and a rollback archive. Separate OpenBao-issued CEO certificate; separate original Agents mTLS client certificate. The CEO certificate is client-only and expires 2026-11-12 05:40:59 UTC. Existing Agents certificate expires 2026-11-11 16:54 UTC.
- Manager (Agents VM) → Control private reservation endpoint: HTTPS 200; independently validated bound `PREPARATION_ONLY` receipt. CEO Control reservation endpoint: HTTPS 200, durable Control ledger row. Two smoke reservations were burned without paid model calls; they do not imply provider invoices or profitable operations.
- One preproduction, receipt-only, human-initiated fixture was signed by the dedicated CEO Ed25519 role on Control, then submitted over CEO-pinned mTLS. Manager (dedicated OS user and Ed25519 role) polled, verified the CEO signature, and returned its own signed `RECEIVED` acknowledgement over Agents-pinned mTLS. CEO independently verified the signed acknowledgement through CEO-only broker status.
- Task: `level2c-authproof-1`. Task status after broker restart: `ACKNOWLEDGED`.
- Assignment issued: `2026-10-29T05:55:18.474029+00:00`. Expiry: `2026-10-29T06:00:18.474029+00:00`. TTL: 300 seconds.
- SHA256 of canonical signed assignment: `1715b145c03a91e5509c16a6e7c6125b0eae8bb63a3a4ddb6edd7641b473fd5c`.
- SHA256 of canonical signed Manager acknowledgement: `aca05dd06c3a772cc2d5e8ca7939cb047d05f6bfcf73dbbdca8fab6767227498`.
- Manager `GET /v1/assignments/pending`: HTTP 200. Manager CEO-only status: HTTP 403. CEO Manager-only polling: HTTP 403.
- Broker restarted; the receipt persisted as `ACKNOWLEDGED`; centralized reservation ledger retained two rows.

## Service and authority boundaries
- Separate role signing seeds and shared public-key trust installed. Role keys remain on their own VMs, in private service-owned directories.
- Dedicated `venture-ceo` and `venture-manager` service units installed with per-role writable state and `ProtectSystem=strict`, `ProtectHome=true`, and no capabilities. Both intentionally remain DISABLED until real provider authentication is available on Agents.
- No business execution, workers, venture launch, payment transfers, customer contact, or finance authorization occurred.

## Blocking conditions for Level 2C acceptance
1. No valid Manager provider credential installed at `/etc/venture-manager-level2c.env`. Attempted secure cross-VM credential-envelope transfer was blocked by host tool safety checks; no credential was copied or exposed.
2. Persistent provider-backed CEO and Manager services have not been started together or shown to continue independently through two Manager acknowledgements.
3. No actual OpenAI inference and no durable provider usage trace on Agents in this integration run.
4. No autonomous restart/recovery test of both running services, and no Claude independent operational acceptance.
5. Direct provider tokens on Managers, if provisioned, require separate audit review of the enforceability of the central budget boundary.

This record is an evidence handoff, NOT production approval.
