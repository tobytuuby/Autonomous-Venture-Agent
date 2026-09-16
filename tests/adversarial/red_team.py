"""Role-bound adversarial identities; deliberately no model imports."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class RedTeamIdentity:
    identity_id: str
    role: str
    venture_id: str | None = None
    def __post_init__(self):
        if self.role not in {"portfolio-ceo", "venture-manager"}:
            raise ValueError("red-team identity must be role-bound")
        if not self.identity_id.startswith("red-team:"):
            raise ValueError("red-team identity namespace required")
CEO_RED_TEAM = RedTeamIdentity("red-team:ceo", "portfolio-ceo")
VM_A_RED_TEAM = RedTeamIdentity("red-team:vm-a", "venture-manager", "venture-a")
VM_B_RED_TEAM = RedTeamIdentity("red-team:vm-b", "venture-manager", "venture-b")
