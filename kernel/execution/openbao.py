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

    def issue(self, service: str) -> Lease:
        request = urllib.request.Request(
            f"{self.address}/v1/auth/token/create",
            data=json.dumps({"policies": ["synthetic-execution"], "ttl": "60s", "renewable": False}).encode(),
            headers={"Content-Type": "application/json", "X-Vault-Token": self.token},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read())
        except Exception as exc:  # pragma: no cover - exercised by integration certification
            raise OpenBaoError("OpenBao lease issuance failed") from exc
        auth = body.get("auth") or {}
        value = auth.get("client_token")
        lease_id = auth.get("accessor") or auth.get("client_token", "")
        duration = int(auth.get("lease_duration", 60))
        if not value or not lease_id:
            raise OpenBaoError("OpenBao returned no synthetic lease")
        return Lease(value=value, lease_id=lease_id, expires_at=datetime.now(timezone.utc) + timedelta(seconds=duration))
