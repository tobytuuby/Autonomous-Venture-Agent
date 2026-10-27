"""Fixed, hash-pinned scheduled intake; no inference, signing or handoff."""
from __future__ import annotations

import os
import stat

from agents.ceo.escalation_inbox import (
    EscalationInbox, MAX_PACKET, digest, inside_root,
)

PACKET = "ventures/venture-001/CEO-ESCALATION-ONLINE-20261027.md"
PACKET_SHA256 = "2f2366519f2235258b5e3b746a965cf2f9652a2eec0a9f480e05b7a39ee2da4b"
ITEM_ID = "studio-online"


def ingest_pending(state):
    """Intake is independent of queue success and never attests CEO processing.

    Packet updates require an explicitly reviewed code/hash change. The durable
    inbox rejects a changed binding for this ID, including after a restart.
    No CEO key is enrolled here; signed review/handoff remains a separate API.
    """
    inbox = None
    try:
        path = inside_root(PACKET)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError("regular unaliased packet required")
            packet = stream.read(MAX_PACKET + 1)
        if digest(packet) != PACKET_SHA256:
            raise ValueError("packet binding denied")
        inbox = EscalationInbox(state / "escalations.sqlite")
        item = inbox.ingest(item_id=ITEM_ID, venture_id="venture-001",
                            source=PACKET, packet=packet)
        # Expose journal state only, never validate or export authority implicitly.
        return 0, dict(status="INBOX_VISIBLE", item_id=item["id"],
                       packet_hash=item["packet_hash"], item_status=item["status"],
                       pending_ceo_review=item["status"] in {
                           "RECEIVED", "ACKNOWLEDGED", "REVIEWED"},
                       required_action="AUTHENTICATED_CEO_DECISION",
                       ceo_work_performed=False, manager_handoff_performed=False,
                       operational_authority=False)
    except Exception:
        # No packet contents, exception text or environment values in status.
        return 4, dict(status="INBOX_DENIED", ceo_work_performed=False,
                       manager_handoff_performed=False, operational_authority=False)
    finally:
        if inbox is not None:
            inbox.close()
