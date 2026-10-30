# Owner API Gate 1 — Security boundary and provisioning requirements

Status: PRE-EXPOSURE; no authorization to activate services.
Reviewed baseline: Control 318c43274f53b9b18e7682c68a47da56f41aa475; CTKFamily 70b0073c93e989bf32c4d17008341e90e2e0a225.

## Scope and data integrity
The Owner API is **research triage only**. Review decisions are advisory; they do not constitute formal owner approval, venture admission, cryptographic authorization, allocation of capital, customer contact, or launch. The current owner_idea_reviews SQLite table is not cryptographically signed or hash-chained, and must not be cited as compliance-grade proof. Formal authorization remains subject to the separately signed Owner authorization policy. This is Option B for advisory record integrity; no new signing key is introduced.

Proposal digests are SHA-256 hashes of each decoded proposal. The UNIQUE(cycle_id,proposal_digest) index prevents duplicate review records for the same digest, but it does **not** prove discovery database immutability. Discovery mutation, deletion, or replacement must be prevented with OS accounts/filesystem permissions and runtime discipline, then demonstrated with operational evidence. No claim of append-only discovery enforcement is made here.

## Minimum deployment contract — not yet implemented
1. Keep the restricted API bound to 127.0.0.1:8792. Do not add a public inbound listener. Use a narrowly scoped authenticated tunnel between CTKFamily and venture-control, terminating at loopback. Do not reuse the CEO↔Workers broker or permit general VM access.
2. Provision a dedicated private CA and distinct server/client certificates with explicit identity and hostname verification. Store private keys in per-service protected files outside Git and document issuance, expiry, renewal, emergency revocation through tunnel/certificate allowlist, and verification failures. Do not reuse CEO identity credentials.
3. Generate an independent high-entropy service bearer token through an owner-controlled provisioning mechanism. Restrict read access to just the required service account(s), never commit or log the token, and provide tested staged rotation/revocation. CTKFamily credentials must have no access to CEO signing keys, finance keys, or VM shell.
4. CTKFamily must require both its existing login and separate Owner verification, with short-lived Owner sessions and synchronizer CSRF token validation. Never rely on X-Owner-Intent alone for browser CSRF protection.
5. Restrict the webserver's outbound access to the Owner API tunnel destination and confirm the Owner API is inaccessible from other hosts. Verify both positive and negative mTLS and token authentication on the deployed route.
6. Add an audit trail of reviewed cycle, proposal digest, actor assertion, decision and receipt time without logging credentials or sensitive private payloads. Test service restart, incomplete request handling, bad certificates, and revoked credentials.

## Pre-exposure proof required
- Confirm systemd service user/working directory, owner database access controls, CA permissions, firewall/tunnel restrictions, operational credential rotation and backup.
- Demonstrate CTKFamily web browser negative authorization/CSRF cases and successful owner review through the secured tunnel.
- Independently review exact CTKFamily commit: pages/venture_ideas.php (underscore in name), plus relevant shared login/session code. The repository must remain private; grant the auditor read-only repository access or supply a signed/hashed source bundle out of band.
- A conditional code-only audit must NOT be treated as approval to open a listener or publish navigation.
- Retain Gate 2 deployed verification as a separate requirement after Gate 1 acceptance.

## Current gaps
Certificates, tunnel, systemd unit, network restriction, token distribution, owner credential configuration, discovery immutability verification and autonomous CEO consumption are not yet demonstrated. No secrets have been provisioned by this document.
