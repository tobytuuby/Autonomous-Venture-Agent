"""No-network simulated payment adapter for P0.9."""
from __future__ import annotations
from threading import Lock


class SimulatedPaymentAdapter:
    def __init__(self, initial_balance=0):
        self._balance = float(initial_balance)
        self._frozen = False
        self._reservations = {}
        self._transactions = []
        self._lock = Lock()

    def balance(self):
        with self._lock:
            return self._balance

    def authorize(self, amount):
        with self._lock:
            return not self._frozen and amount > 0 and amount <= self._balance

    def reserve(self, reservation_id, amount):
        with self._lock:
            if self._frozen or amount <= 0 or amount > self._balance:
                return False
            if reservation_id in self._reservations:
                return True
            self._reservations[reservation_id] = float(amount)
            return True

    def capture(self, reservation_id):
        with self._lock:
            amount = self._reservations.pop(reservation_id, None)
            if amount is None or self._frozen or amount > self._balance:
                return False
            self._balance -= amount
            self._transactions.append(("capture", reservation_id, amount))
            return True

    def refund(self, transaction_id, amount):
        with self._lock:
            if amount <= 0:
                return False
            self._balance += float(amount)
            self._transactions.append(("refund", transaction_id, float(amount)))
            return True

    def freeze(self):
        with self._lock:
            self._frozen = True

    def unfreeze(self):
        with self._lock:
            self._frozen = False

    def transactions(self):
        with self._lock:
            return tuple(self._transactions)
