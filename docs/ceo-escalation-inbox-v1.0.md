# Durable CEO escalation inbox v1.0

Local implementation guide, 2026-10-27. This adds preparation intake and a decision/handoff record boundary under [owner approval policy](owner-venture-approval-policy-v1.0.md); it changes no policy, phase acceptance, live authority, approval or budget.

**The fixed scheduled CEO service cannot consume this inbox automatically until separately wired and validated.** No scheduler, provider, worker, manager executor or service deployment is added. Venture #1 remains an unapproved pilot. Ingesting its escalation does not accept the product or create a CEO decision.

## Operator CLI

Run from the approved project root. Create a private state directory inside the project first; do not point this CLI at existing scheduler or venture databases.

```sh
mkdir -m 700 -p artifacts/ceo-escalations
python3 -m agents.ceo.escalation_inbox --database artifacts/ceo-escalations/inbox.sqlite ingest --id studio-online-20261027 --venture venture-001 --file ventures/venture-001/CEO-ESCALATION-ONLINE-20261027.md
python3 -m agents.ceo.escalation_inbox --database artifacts/ceo-escalations/inbox.sqlite read --id studio-online-20261027
python3 -m agents.ceo.escalation_inbox --database artifacts/ceo-escalations/inbox.sqlite ack --id studio-online-20261027 --actor operator
```

CLI read returns packet content: only ingest reviewed, secret-free text. Source is an operator-supplied provenance label, not authenticated sender identity. SHA-256 binds the exact UTF-8 packet bytes. The CLI rejects paths outside the root and symlink aliases, bounds file reads, and emits a generic error without exception bodies. Ingest/read/ack cannot authorize a decision. No actual pilot DB ingestion or CEO processing is claimed by tests.

## State and strict review contract

SQLite FULL synchronization and BEGIN IMMEDIATE serialize mutation, duplicate detection, capacity checks, event append and snapshot writes in one commit. Identical ingestion ID and binding replay without another event; changed content, venture or source under that ID is denied. Bounds: 1,000 total immutable intake items, 64 KiB per packet, 5,000 audit events, eight review instructions, 600 characters per instruction/summary/owner request, 96-character ASCII identifiers. At capacity, fail closed; no automatic deletion or archival.

Transitions: RECEIVED → ACKNOWLEDGED → REVIEWED → HANDOFF_READY, HOLD or DENIED. Ack is receipt acknowledgment only. Review is advisory data only. Invalid input leaves the previous non-authorizing state intact. Decisions and reviews are immutable; corrections require a new intake ID and packet, never silent replacement.

The executable strict schema is `validate_review` in `agents/ceo/escalation_inbox.py`. Exact object keys, types, lengths, enum, IDs and lineage are mandatory; additional keys are denied:

| Field | Required value |
| --- | --- |
| item_id | exact inbox ID |
| packet_hash | exact intake SHA-256 |
| disposition | HANDOFF, HOLD or DENIED |
| summary | nonempty string, at most 600 characters |
| manager_id | bounded ASCII identifier |
| instructions | list of 0–8 nonempty strings, each at most 600 characters; HANDOFF needs at least one |
| owner_action | null or nonempty string, at most 600 characters |
| scope | PREPARATION_ONLY |

Trusted code calls `record_review(item_id, review, evidence_source=...)`. Provenance must be fixture, operator_supplied, or configured_provider_not_independently_verified. A fixture is never real provider inference. This module makes zero provider requests and supplies no fallback inference. Review text is untrusted data and is never executed.

## Actual decision gate and manager handoff

A future trusted control-plane adapter must pin the public key of an independently authorized CEO decision signer via the constructor's `ceo_public_key`. No key is configured by default; there is no CLI key enrollment, private-key loader, signer, autoapproval, inference bridge or model-driven authorization. Supplying a key is a deployment trust decision, not permission granted by this guide. Do not wire a model response directly into a signer.

`record_decision(item_id, receipt, signature)` requires an Ed25519 signature over UTF-8 canonical JSON (sorted keys, compact separators, no NaN). The receipt has exactly venture_id, item_id, packet_hash, review_hash (SHA-256 of canonical review), manager_id, decision (same as review disposition), scope (PREPARATION_ONLY), ceo_id, decision_reference, issued_at and expires_at. Identity/reference text is covered by the pinned signer attestation. Validity timestamps must be timezone-aware, current, and at most 24 hours apart. Signature, raw receipt and verifier key hash are retained atomically. No receipt is fabricated in runtime code.

`handoff(item_id, manager_id)` exports only HANDOFF_READY records, rechecks signature, current pinned key, expiry, manager and full binding, and records the first export in the audit chain. Repeated export is idempotent. It returns the exact review and signed decision plus explicit false operational/external-action/worker-autoexec flags and true owner-approval-required. It never invokes the existing manager or advisory queue. A downstream manager must independently enforce current owner approval and every existing authority gate before any operational execution; these handoff records are not executable capabilities.

## Audit and limitations

Every event hashes sequence, previous hash, timestamp, kind and complete snapshot. Every public read/mutation verifies contiguous event order and equality of current snapshots to their latest events. Corrupt events, changed snapshots and a deleted tail with retained state fail closed. Tests cover rollback after event and snapshot writes, concurrent same-ID ingestion, restart and replay.

Local hashes are tamper evidence, not external anchoring. A privileged attacker can rewrite an entire chain, remove both state and history, or restore a complete older database. Database/key isolation, secure backups, external anchoring, revocation and a safe signer/service integration remain future work. Filesystem path validation assumes a trusted local control plane; it is not protection from a privileged concurrent filesystem attacker. Only the signer attestation is verified: neither an actual discussion nor real provider reasoning is independently established. In-memory ephemeral test keys are synthetic signing fixtures only.

## Validation and review

`python3 -m unittest tests.test_ceo_escalation_inbox -v` exercises the existing Studio Restock Kit escalation as packet data with synthetic reviews and signatures. Full regression uses `python3 -m unittest discover -s tests -v`. This is supplemental local workflow evidence, not ADV recertification; ADV-001–ADV-049 and /49 remain unchanged. Raw outputs and hashes are recorded in the [evidence directory](../tests/certification/ceo-inbox-20261027/REVIEW.md).

Operator impact: a durable receipt/read/ack path now exists; a reviewed packet remains blocked without a signed decision. No owner approval, live credential, actual capital, real CEO attachment, deployment or external action is used. Review decision: suitable for local preparation workflow review only; automatic service consumption and operational use remain unwired.
