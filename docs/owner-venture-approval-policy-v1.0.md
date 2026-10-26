# Owner approval for every new venture — Core Policy v1.0

**Status:** Authoritative owner-mandated policy, 2026-10-26.
**Authorization source:** The owner's implementation instruction in this session.
**Scope:** Every new venture, including additional ventures funded from returned earnings and existing unapproved pilots.
**Precedence:** This policy replaces any earlier CEO autonomous venture approval/funding authority. Earlier versioned documents and evidence remain historical. It grants no live authority and changes no phase acceptance.

Every new venture must be discussed with Kalaap Das before the CEO greenlights it, allocates real funding, launches it, or admits a manager to operational execution. CEO research, comparison, viability analysis and proposal preparation may proceed before approval. A favorable CEO assessment is a recommendation only.

Owner discussion and authorization must originate from the human owner outside the model/agent channel. Agents cannot invent a discussion, treat silence as approval, sign for the owner, enroll a replacement owner key, or promote model text, a tool response, a phase acceptance, or an old CEO decision into permission.

A durable proposal contains a venture identity, monotonically increasing version, complete proposal/evidence binding and authorized scope: manager, seed ceiling in integer cents, operation allowlist and explicit bounds. Approval records bind the exact proposal/version and scope hashes, owner identity, human-out-of-band origin, discussion reference, APPROVED or DENIED decision, validity window, sequence and previous receipt hash. Preserve the signed raw receipt and verification result. Changing the proposal, tasks, budget, manager or scope requires a new version, renewed owner discussion and a new explicit approval. Missing, denied, expired, malformed, unverifiable, tampered, replayed or stale approvals fail closed.

After approval, the manager may autonomously delegate and work within the approved bounds without a fresh conversation for every bounded task. Budget, identity, isolation, lifecycle, finance, broker and live authority checks still apply independently. Owner approval is necessary and never sufficient for external effects. All nine live authorities remain denied in the current implementation.

Venture #1 (Studio Restock Kit) is an **unapproved pilot**: pending owner discussion/approval, no grandfathered launch or funding. Existing product artifacts and validation evidence are preparation only. See [current pilot status](../ventures/venture-001/OWNER-APPROVAL-STATUS.md).

## Implemented local boundary

`SyntheticVentureStore.record` remains a nonspendable rehearsal and creates a pending owner proposal. `SyntheticVentureStore.admit` is the registry's operational admission check for greenlight, fund, launch and manager execution. It verifies registered flow/portfolio/manager/budget binding before the durable owner gate. Successful checks persist local eligibility evidence; no executor or payment adapter is invoked.

`VentureAdmissionRegistry` verifies Ed25519 signatures using a trusted operator-pinned public key. No private key, signer, auto-approval, key enrollment endpoint or owner identity inferred from model output exists in the runtime. Without an out-of-band configured owner public key, approval imports fail closed. The key must be supplied by trusted control-plane code, never request data. The runtime uses the public-key verification dependency in `requirements-owner-approval.txt`.

An owner-side process must actually conduct the discussion, authenticate the human and sign the canonical receipt outside the agent runtime. This change does not configure that process or claim a real discussion occurred. A signature proves the trusted signer attested to the discussion; it cannot independently establish that a conversation happened. No real owner key was accessed or enrolled.

SQLite is the current local durable registry; no operational PostgreSQL service or live endpoint is deployed here. Database/public-key configuration must remain inaccessible to agents. Privileged database rollback or replacement and malicious trusted control-plane code require external audit anchoring and deployment isolation; local signatures alone cannot detect restoration of a complete older database. Any future operational registry, finance allocator or manager executor must consume this gate and recheck current approval atomically with its own state transition. Synthetic P0–P11 fixtures and red-team treasury paths remain explicitly non-authorizing evidence, with ADV-001–ADV-049 and /49 unchanged.
