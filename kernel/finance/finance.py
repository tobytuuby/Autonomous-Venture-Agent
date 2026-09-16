"""Treasury and capital-allocation controls for P0.9."""
from __future__ import annotations
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class TreasuryPolicy:
    protected_cash_floor_pct: float = 0.50
    operating_reserve_pct: float = 0.20
    max_portfolio_deployable_pct: float = 0.30
    max_new_venture_funding_pct: float = 0.10
    venture_reinvestment_pct: float = 0.20


class FinancialGovernor:
    def __init__(self, eligible_balance: float, policy: TreasuryPolicy | None = None):
        self.policy = policy or TreasuryPolicy()
        self.eligible_balance = float(eligible_balance)
        self.deployed = 0.0
        self.new_venture_deployed = 0.0
        self._lock = Lock()

    @property
    def deployable_ceiling(self):
        return self.policy.max_portfolio_deployable_pct * self.eligible_balance

    @property
    def new_venture_ceiling(self):
        return self.policy.max_new_venture_funding_pct * self.eligible_balance

    def allocate(self, amount: float, new_venture: bool = False) -> bool:
        with self._lock:
            if amount <= 0:
                return False
            if self.eligible_balance < self.deployed:
                return False
            if self.deployed + amount > self.deployable_ceiling:
                return False
            if new_venture and self.new_venture_deployed + amount > self.new_venture_ceiling:
                return False
            self.deployed += amount
            if new_venture:
                self.new_venture_deployed += amount
            return True

    def update_balance(self, eligible_balance: float):
        with self._lock:
            self.eligible_balance = float(eligible_balance)

    def sweep_profit(self, settled_revenue, refunds, chargebacks, taxes, liabilities, infra_cost):
        available = max(0.0, settled_revenue - refunds - chargebacks - taxes - liabilities - infra_cost)
        return {"treasury_sweep": available, "available_profit": available,
                "venture_reinvestment": available * self.policy.venture_reinvestment_pct}

    def request_runway_draw(self, actor_role: str, amount: float, venture_balance: float, protected_reserve: float) -> bool:
        if actor_role != "portfolio-ceo":
            return False
        return amount > 0 and venture_balance - amount >= protected_reserve and self.allocate(amount)

    def reinvest_profit(self, actor_role: str, amount: float) -> bool:
        if actor_role != "portfolio-ceo":
            return False
        return self.allocate(amount)

    def classify_expense(self, category: str):
        opex = {"inference", "hosting", "software", "advertising", "contractor"}
        capex = {"equipment", "durable-license"}
        if category in opex:
            return "opex"
        if category in capex:
            return "capex"
        return None
