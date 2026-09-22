"""Synthetic-only credential custody and provider-boundary controls for P7.4."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .recovery import LIVE_AUTHORITIES


class ProviderBoundaryError(ValueError):
    """Raised when a credential or provider boundary must fail closed."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class CredentialRecord:
    credential_id: str
    handle: str
    version: int
    provider_id: str
    owner: str
    status: str
    lineage: tuple[str, ...]
    evidence_hash: str

    def public(self) -> dict[str, Any]:
        return {
            "credential_id": self.credential_id,
            "handle": self.handle,
            "version": self.version,
            "provider_id": self.provider_id,
            "owner": self.owner,
            "status": self.status,
            "lineage": list(self.lineage),
            "evidence_hash": self.evidence_hash,
            "synthetic_only": True,
            "live_credential": False,
            "external_action": False,
            "unauthorized_action": False,
        }


class SyntheticProviderBoundary:
    """In-memory custody and provider-admission fixture with no external I/O."""

    def __init__(
        self,
        *,
        source_commit: str,
        config_fingerprint: str,
        environment: str = "p7.4-isolated",
        reviewer: str = "Kalaap Das",
    ) -> None:
        self.source_commit = source_commit
        self.config_fingerprint = config_fingerprint
        self.environment = environment
        self.reviewer = reviewer
        self._secrets: dict[str, str] = {}
        self._records: dict[str, CredentialRecord] = {}
        self._providers: dict[str, str] = {}
        self.revocations: list[dict[str, Any]] = []
        self.fail_closed = False

    @staticmethod
    def authorities() -> dict[str, bool]:
        return {name: False for name in LIVE_AUTHORITIES}

    @staticmethod
    def model_output_authorizes_execution(model_output: Mapping[str, Any]) -> bool:
        del model_output
        return False

    def _guard(self) -> None:
        if self.fail_closed:
            raise ProviderBoundaryError("provider boundary is terminal fail-closed")

    @staticmethod
    def _is_sha256(value: Any) -> bool:
        return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None

    @staticmethod
    def _synthetic_secret(value: Any) -> bool:
        return isinstance(value, str) and value.startswith("synthetic-secret-") and len(value) >= 18

    @staticmethod
    def _redact(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): "[REDACTED]" if any(
                    token in str(key).lower()
                    for token in ("secret", "token", "password", "private_key", "credential_value")
                ) else SyntheticProviderBoundary._redact(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [SyntheticProviderBoundary._redact(item) for item in value]
        if isinstance(value, tuple):
            return [SyntheticProviderBoundary._redact(item) for item in value]
        return value

    def _evidence_hash(self, material: Mapping[str, Any]) -> str:
        return _sha256(_canonical({
            "source_commit": self.source_commit,
            "config_fingerprint": self.config_fingerprint,
            "environment": self.environment,
            "material": dict(material),
        }))

    def register_provider(self, *, provider_id: str, dependency_sha256: str, live_provider: bool = False) -> dict[str, Any]:
        self._guard()
        if live_provider or provider_id.startswith("live-"):
            raise ProviderBoundaryError("live provider denied")
        if not provider_id or not self._is_sha256(dependency_sha256):
            raise ProviderBoundaryError("provider requires a pinned SHA-256 dependency")
        self._providers[provider_id] = dependency_sha256
        return {
            "provider_id": provider_id,
            "dependency_sha256": dependency_sha256,
            "environment": self.environment,
            "synthetic_only": True,
            "external_action": False,
            "live_credential": False,
        }

    def create_credential(
        self,
        *,
        credential_id: str,
        owner: str,
        provider_id: str,
        secret_material: str,
    ) -> dict[str, Any]:
        self._guard()
        if provider_id not in self._providers:
            raise ProviderBoundaryError("provider is not allowlisted")
        if not credential_id or not owner or not self._synthetic_secret(secret_material):
            raise ProviderBoundaryError("only synthetic credential material is accepted")
        if credential_id in self._records:
            raise ProviderBoundaryError("credential identity already exists")
        handle = _sha256(_canonical({
            "credential_id": credential_id, "version": 1,
            "source_commit": self.source_commit, "environment": self.environment,
        }))
        record = CredentialRecord(
            credential_id, handle, 1, provider_id, owner, "ACTIVE", (handle,),
            self._evidence_hash({"operation": "create", "handle": handle}),
        )
        self._records[credential_id] = record
        self._secrets[handle] = secret_material
        return record.public()

    def _record(self, credential_id: str) -> CredentialRecord:
        record = self._records.get(credential_id)
        if record is None:
            raise ProviderBoundaryError("unknown synthetic credential")
        return record

    def _active_record(self, credential_id: str) -> CredentialRecord:
        record = self._record(credential_id)
        if record.status != "ACTIVE":
            raise ProviderBoundaryError("credential is not active")
        return record

    def rotate(
        self,
        *,
        credential_id: str,
        actor: str,
        new_secret_material: str,
        inject_failure: bool = False,
    ) -> dict[str, Any]:
        self._guard()
        if actor != "synthetic-operator":
            raise ProviderBoundaryError("unauthorized rotation actor")
        old = self._active_record(credential_id)
        if not self._synthetic_secret(new_secret_material):
            raise ProviderBoundaryError("rotation requires synthetic credential material")
        if inject_failure:
            self.fail_closed = True
            raise ProviderBoundaryError("injected rotation failure; terminal fail-closed")
        new_version = old.version + 1
        new_handle = _sha256(_canonical({
            "credential_id": credential_id, "version": new_version,
            "source_commit": self.source_commit, "environment": self.environment,
        }))
        lineage = old.lineage + (new_handle,)
        self._secrets.pop(old.handle, None)
        self._secrets[new_handle] = new_secret_material
        record = CredentialRecord(
            credential_id, new_handle, new_version, old.provider_id, old.owner,
            "ACTIVE", lineage,
            self._evidence_hash({"operation": "rotate", "old_handle": old.handle, "new_handle": new_handle}),
        )
        self._records[credential_id] = record
        return record.public()

    def revoke(
        self,
        *,
        credential_id: str,
        actor: str,
        inject_failure: bool = False,
    ) -> dict[str, Any]:
        self._guard()
        if actor != "synthetic-operator":
            raise ProviderBoundaryError("unauthorized revocation actor")
        old = self._active_record(credential_id)
        if inject_failure:
            self.fail_closed = True
            raise ProviderBoundaryError("injected revocation failure; terminal fail-closed")
        self._secrets.pop(old.handle, None)
        record = CredentialRecord(
            old.credential_id, old.handle, old.version, old.provider_id, old.owner,
            "REVOKED", old.lineage,
            self._evidence_hash({"operation": "revoke", "handle": old.handle}),
        )
        self._records[credential_id] = record
        revocation = {
            "credential_id": credential_id,
            "handle": old.handle,
            "status": "REVOKED",
            "evidence_hash": record.evidence_hash,
            "source_commit": self.source_commit,
            "configuration_fingerprint": self.config_fingerprint,
            "environment": self.environment,
            "external_action": False,
            "live_credential": False,
        }
        self.revocations.append(revocation)
        return dict(revocation)

    def provider_request(
        self,
        *,
        credential_id: str,
        provider_id: str,
        payload: Mapping[str, Any],
        dependency_sha256: str,
        source_commit: str | None = None,
        config_fingerprint: str | None = None,
        environment: str | None = None,
        live_provider: bool = False,
    ) -> dict[str, Any]:
        self._guard()
        if live_provider or provider_id.startswith("live-"):
            raise ProviderBoundaryError("live provider denied")
        if provider_id not in self._providers:
            raise ProviderBoundaryError("provider is not allowlisted")
        if dependency_sha256 != self._providers[provider_id]:
            raise ProviderBoundaryError("dependency fingerprint mismatch")
        if source_commit not in (None, self.source_commit):
            raise ProviderBoundaryError("source binding mismatch")
        if config_fingerprint not in (None, self.config_fingerprint):
            raise ProviderBoundaryError("configuration binding mismatch")
        if environment not in (None, self.environment):
            raise ProviderBoundaryError("environment binding mismatch")
        record = self._active_record(credential_id)
        if record.provider_id != provider_id:
            raise ProviderBoundaryError("credential provider mismatch")
        projection = {
            "provider_id": provider_id,
            "dependency_sha256": dependency_sha256,
            "credential_handle": record.handle,
            "credential_version": record.version,
            "payload": self._redact(dict(payload)),
            "source_commit": self.source_commit,
            "configuration_fingerprint": self.config_fingerprint,
            "environment": self.environment,
            "synthetic_only": True,
            "dispatch": False,
            "external_action": False,
            "unauthorized_action": False,
            "live_credential": False,
            "live_authorities": self.authorities(),
        }
        return projection

    def inject_failure(self, control: str) -> None:
        self._guard()
        if control not in {"custody", "rotation", "revocation", "allowlist", "dependency", "redaction"}:
            raise ProviderBoundaryError("unknown injected failure")
        self.fail_closed = True
        raise ProviderBoundaryError(f"injected {control} failure; terminal fail-closed")

    def public_record(self, credential_id: str) -> dict[str, Any]:
        self._guard()
        return self._record(credential_id).public()
