"""Minimal OpenBao HTTP lease client used only by the internal execution service."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta, timezone

from .execution_service import Lease


class OpenBaoError(RuntimeError):
    pass


class OpenBaoLeaseClient:
    def __init__(self, address: str, token: str, timeout: float = 5.0):
        self.address = address.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _request(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            f"{self.address}{path}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "X-Vault-Token": self.token},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read() or b"{}")
        except Exception as exc:  # pragma: no cover - exercised by integration certification
            raise OpenBaoError("OpenBao request failed") from exc

    def issue(self, service: str) -> Lease:
        body = self._request("/v1/auth/token/create", {"policies": ["synthetic-execution"], "ttl": "60s", "renewable": False})
        auth = body.get("auth") or {}
        value = auth.get("client_token")
        lease_id = auth.get("accessor") or auth.get("client_token", "")
        duration = int(auth.get("lease_duration", 60))
        if not value or not lease_id:
            raise OpenBaoError("OpenBao returned no synthetic lease")
        return Lease(value=value, lease_id=lease_id, expires_at=datetime.now(timezone.utc) + timedelta(seconds=duration))

    def revoke(self, lease_id: str) -> None:
        # Token accessors are revoked through the token auth method, not the generic lease path.
        self._request("/v1/auth/token/revoke-accessor", {"accessor": lease_id})
