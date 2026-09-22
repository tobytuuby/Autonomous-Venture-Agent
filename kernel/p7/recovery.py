"""Synthetic-only backup, restore, and disaster-recovery controls for P7.2."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


LIVE_AUTHORITIES = (
    "network", "broker", "payment", "credential", "deployment",
    "customer", "capital", "venture", "worker",
)


class RecoveryError(ValueError):
    """Raised when a synthetic backup cannot be safely verified or restored."""



def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class RecoveryObjectives:
    rpo_target_seconds: int
    rto_target_seconds: int
    observed_rpo_seconds: int
    observed_rto_seconds: int

    def as_dict(self) -> dict[str, int]:
        return {
            "rpo_target_seconds": self.rpo_target_seconds,
            "rto_target_seconds": self.rto_target_seconds,
            "observed_rpo_seconds": self.observed_rpo_seconds,
            "observed_rto_seconds": self.observed_rto_seconds,
        }


class SyntheticRecoveryManager:
    """In-memory recovery model; it has no filesystem, network, or service I/O."""

    def __init__(self, *, source_commit: str, config_fingerprint: str,
                 environment: str = "p7.2-isolated", reviewer: str = "Kalaap Das") -> None:
        self.source_commit = source_commit
        self.config_fingerprint = config_fingerprint
        self.environment = environment
        self.reviewer = reviewer
        self.current_state: dict[str, Any] = {}
        self.quarantine: list[bytes] = []

    @staticmethod
    def authorities() -> dict[str, bool]:
        return {name: False for name in LIVE_AUTHORITIES}

    @staticmethod
    def model_output_authorizes_execution(model_output: Mapping[str, Any]) -> bool:
        """Model text/fields cannot grant execution authority."""
        del model_output
        return False

    def set_state(self, state: Mapping[str, Any]) -> None:
        self.current_state = json.loads(_canonical(dict(state)))

    def state_hash(self, state: Mapping[str, Any] | None = None) -> str:
        return _sha256(_canonical(self.current_state if state is None else dict(state)))

    def create_backup(self, *, created_at: str = "2026-09-22T00:00:00Z") -> bytes:
        state = json.loads(_canonical(self.current_state))
        manifest = {
            "schema": "p7.2.synthetic-backup.v1",
            "source_commit": self.source_commit,
            "config_fingerprint": self.config_fingerprint,
            "environment": self.environment,
            "created_at": created_at,
            "reviewer": self.reviewer,
            "synthetic_only": True,
            "external_action": False,
            "live_credential": False,
            "unauthorized_action": False,
            "live_authorities": self.authorities(),
            "state_hash": self.state_hash(state),
        }
        unsigned = {"manifest": manifest, "state": state}
        backup_hash = _sha256(_canonical(unsigned))
        envelope = {**unsigned, "backup_hash": backup_hash}
        return _canonical(envelope)

    def verify_backup(self, backup: bytes) -> dict[str, Any]:
        try:
            envelope = json.loads(backup.decode("utf-8"))
            manifest = envelope["manifest"]
            state = envelope["state"]
            recorded_backup_hash = envelope["backup_hash"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RecoveryError("incomplete or invalid backup envelope") from exc
        if not isinstance(manifest, dict) or not isinstance(state, dict):
            raise RecoveryError("manifest and state must be objects")
        unsigned = {"manifest": manifest, "state": state}
        if _sha256(_canonical(unsigned)) != recorded_backup_hash:
            raise RecoveryError("backup checksum mismatch")
        required = {"schema", "source_commit", "config_fingerprint", "environment", "created_at",
                    "reviewer", "synthetic_only", "external_action", "live_credential",
                    "unauthorized_action", "live_authorities", "state_hash"}
        if not required.issubset(manifest):
            raise RecoveryError("backup manifest is incomplete")
        if manifest["schema"] != "p7.2.synthetic-backup.v1":
            raise RecoveryError("unsupported backup schema")
        if manifest["source_commit"] != self.source_commit:
            raise RecoveryError("source commit mismatch")
        if manifest["config_fingerprint"] != self.config_fingerprint:
            raise RecoveryError("configuration fingerprint mismatch")
        if manifest["environment"] != self.environment:
            raise RecoveryError("environment identity mismatch")
        if manifest["synthetic_only"] is not True or manifest["external_action"] is not False:
            raise RecoveryError("backup is not synthetic-only")
        if manifest["live_credential"] is not False or manifest["unauthorized_action"] is not False:
            raise RecoveryError("unsafe backup metadata")
        if manifest["live_authorities"] != self.authorities():
            raise RecoveryError("live authority widening detected")
        if self.state_hash(state) != manifest["state_hash"]:
            raise RecoveryError("authoritative state hash mismatch")
        return envelope

    def restore(self, backup: bytes, *, inject_failure: bool = False) -> str:
        envelope = self.verify_backup(backup)
        previous = self.current_state
        if inject_failure:
            self.quarantine.append(backup)
            self.current_state = previous
            raise RecoveryError("injected restore failure contained")
        self.current_state = json.loads(_canonical(envelope["state"]))
        return self.state_hash()

    def recover_service_loss(self, backup: bytes) -> str:
        return self.restore(backup)

    def recover_host_loss(self, backup: bytes) -> str:
        return self.restore(backup)

    def objectives(self) -> RecoveryObjectives:
        return RecoveryObjectives(60, 120, 0, 1)
