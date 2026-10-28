# OR-0.10 Level 2B — Control Broker mTLS Transport and Polling Route Amendment (DRAFT)

Version: v0.1 | Date: 2026-10-28 | Status: **OWNER APPROVAL REQUIRED — NOT AUTHORIZING IMPLEMENTATION**
Scope: Option A only; existing Control port TCP/8443, Agents-to-Control read-only preparation polling, no outbound/financial authorities.
Baseline: `main` at `00519e09d4a72f76590e9b6212c998432b4f240f`.
Related: `docs/operational-viability-project-plan-v2.4.md`, `docs/operational-readiness/OR-0.10-level1-independent-audit.md`, `infrastructure/README.md`.

## 1. Verified current state and problem

Control's deployed `/usr/local/lib/venture-control-broker/kernel/broker/server.py` matches repository `kernel/broker/server.py` by SHA-256 and serves **plaintext** `ThreadingHTTPServer(("0.0.0.0", 8443), Handler)`. It accepts `GET /health` and `POST /v1/capabilities/evaluate`; there is no TLS, client certificate, identity-specific path policy, or polling route. The systemd service runs as `venture-broker`; UFW permits Agents (192.168.0.116) to Control (192.168.0.167) on 8443 only. Firewall source restrictions do not provide mutual authentication or encryption. There must be no assertion that the port is already HTTPS.

Control's OpenBao service is installed and locally bound on 127.0.0.1:8200. Agents has OpenSSL but no OpenBao service. Existing Cloudflare bridge tunnels are management-plane connections, not the approved agent protocol. Audited polling code requires loopback binding and verified client certificates; no active network service or real end-to-end mTLS execution has been demonstrated.

## 2. Proposed narrow change (subject to owner approval)

**Route direction:** Agents **polls Control** for signed, bounded PREPARATION_ONLY assignments. Completion acknowledgments do not constitute work execution evidence.

- Keep **only** existing Control ingress TCP/8443 from Agents; no new LAN listener, public endpoint, agent-side root/SSH reachability, or firewall widening. Do not casually extend the existing plaintext handler.
- Upgrade 8443 to authenticated TLS. Require a trusted, short-lived, dedicated **Agents client certificate** and validate certificate chain, validity, expected identity (SAN/EKU), and cryptographically pinned certificate or issuer+identity. Require a dedicated Control server identity, with Agents verifying trusted CA and hostname/SAN. No optional client certificates or plaintext fallback.
- Restrict polling to exact `GET /v1/assignments/pending`; deny unexpected method, path, query, redirects, bodies, and unauthenticated or wrong-role clients. Content remains read-only and signed. Ensure transport identity cannot be impersonated using forwarded headers.
- Preserve `GET /health` and `POST /v1/capabilities/evaluate` semantics, but require authenticated TLS at the outer boundary for **both** routes. No unauthenticated alternate localhost or public plaintext capability path. Evaluate whether different client certificates/roles are required per route; deny all unidentified callers.
- Keep the tested polling implementation on loopback if separated from the 8443 listener. A broker routing adapter may only connect internally to this endpoint with a strongly authenticated channel; do not pass attacker-controlled identity headers. **If preserving this isolation requires bypassing TLS/mTLS at any trust boundary, stop Option A and submit Option D for separate approval.**
- Use existing Control OpenBao only **after verifying** its health/unsealed state, configured PKI capability, privileges, audit trail, CA lifecycle, rotation and revocation plan. Never expose OpenBao to Agents; do not provision long-lived root or intermediate signing keys into the project checkout. Avoid committing keys, full certificates with sensitive identity metadata, tokens or bearer credentials.
- Do not issue manager/worker execution authority, enable a CEO, sign an owner approval, launch a venture, contact customers, or allow payment/spending; OR-0.10 Level 2C remains independently gated.

## 3. Compatibility discovery and blocking test plan

Before any production cutover, inventory **every caller** of TCP/8443 (including agent-side code, local health monitors, curl/systemd tests and external operational clients); capture endpoint, HTTP method, authentication status, service account and expected response. This inventory is a blocking deliverable. Merely preserving JSON responses does **not** mean plaintext clients continue to work after a mandatory mTLS upgrade.

Implement and test on isolated binding/fixtures first; no restart or live port change until:
1. Positive mTLS: pinned Agents cert succeeds; trusted server name/SAN and chain are checked; exact polling request yields signed pending-envelope metadata without executing assignments.
2. Negative TLS: absent cert, wrong CA, wrong client identity/SAN, expired/revoked cert, hostname mismatch, tampered chain, TLS downgrade and plaintext attempt all fail closed.
3. Negative routing: wrong methods/path/query, hostile forwarded identity headers, malformed/oversized requests and unauthorized certificate roles cannot access either endpoint.
4. Regression: authorized `GET /health` returns the same payload/status; authorized `POST /v1/capabilities/evaluate` yields the same validated decision and denial behavior as current baseline, including OPA-denied and malformed-request cases.
5. Client migration: update **all known callers** to verified mTLS first and demonstrate success; clients not accounted for prohibit cutover. Prove there is no old plaintext path into the broker.
6. Recovery: connection interruption, service restart, certificate rollover and agent reconnect do not cause duplicate task delivery or authority widening. Explicitly measure route latency and document acceptable threshold before certification.
7. Observe logs sanitized for identity and denial outcomes; never include private keys, auth tokens, request bodies, or personal data in GitHub evidence.

**Go/no-go:** owner-approved scope + passed isolated tests + complete caller inventory/migration + reproducible negative cases + rollback tested + sanitized evidence reviewed. Fail closed when evidence is missing.

## 4. Cutover and rollback

Record current service source hash, unit hash, effective firewall, listeners, health response, OPA health, caller list and test baseline before changes. Deploy reversible, versioned configuration under existing `venture-broker` account and sandboxing; stage cert material outside repository with minimum read access. Preserve the approved firewall. A test-only diagnostic route must not accept or execute tasks.

If mTLS handshake fails, broker regression fails, a client breaks, a plaintext fallback appears, or identities can cross routes, **stop immediately**. Roll back using the saved service/configuration snapshot only after ensuring reversion cannot restore an exposed unauthenticated sensitive path. If safe rollback to plaintext would violate the new security policy, leave broker unavailable (fail closed) pending explicit owner risk decision. Never silently downgrade.

## 5. Required evidence and decision

Produce versioned test commands, exit statuses, sanitized logs, certificate fingerprints/public metadata and validity (no keys), service/config SHA-256, route/firewall observations, client inventory and migration tests, positive/negative matrix, latency, restart/recovery result, and residual risks. Commit sanitized artifacts to GitHub, then request Claude's independent Level 2 review. Claude's review is not owner approval.

**Owner decision requested:** Approve or reject the **narrow policy amendment and isolated test preparation**. A separate explicit owner authorization is required for certificate issuance and production broker cutover after the caller inventory and safe migration design are reviewed. No automatic progression into signed assignment delivery or worker execution.

Decision: **PENDING OWNER**. No policy activation, keys, certificates, firewall changes, service restarts or authority grants occur by committing this draft.
