"""P6.5 synthetic end-to-end portfolio certification composition."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .anomaly import SyntheticAnomalyAnalyzer, build_analysis_request
from .coordination import SyntheticCoordinationKernel, build_coordination_packet
from .operations import SyntheticOperationsKernel, build_operation
from .registry import LIVE_FIELDS, SyntheticPortfolioRegistry, build_membership, build_portfolio, canonical, digest
from .shared_service import SyntheticSharedServiceRunner, build_demand


class PortfolioCertificationDenied(ValueError):
    """Raised when the P6.5 composition cannot complete fail-closed."""


class SyntheticPortfolioCertification:
    """Compose accepted P6 kernels for two ventures and one shared service."""

    def __init__(
        self,
        *,
        configuration_fingerprint: str,
        portfolio_id: str = "portfolio-p65",
        venture_ids: tuple[str, str] = ("venture-a", "venture-b"),
        clock: datetime | None = None,
    ):
        if len(venture_ids) != 2 or len(set(venture_ids)) != 2:
            raise PortfolioCertificationDenied("P6.5 requires exactly two distinct ventures")
        self.configuration_fingerprint = configuration_fingerprint
        self.portfolio_id = portfolio_id
        self.venture_ids = venture_ids
        self.now = (clock or datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)).astimezone(timezone.utc)
        self.timestamp = self.now.isoformat()
        self.expiry = (self.now.replace(hour=13)).isoformat()
        self.registry = SyntheticPortfolioRegistry(configuration_fingerprint)
        self.coordination = SyntheticCoordinationKernel(
            self.registry,
            policy_version="p6.1",
            configuration_fingerprint=configuration_fingerprint,
            clock=lambda: self.now,
        )
        self.shared_service = SyntheticSharedServiceRunner(
            self.registry,
            policy_version="p6.2",
            configuration_fingerprint=configuration_fingerprint,
            service_limits={"metadata-read": 10},
            clock=lambda: self.now,
        )
        self.analyzer = SyntheticAnomalyAnalyzer(
            policy_version="p6.3",
            configuration_fingerprint=configuration_fingerprint,
        )
        self.operations = SyntheticOperationsKernel(
            "p6.4",
            configuration_fingerprint,
            allowed_ventures={portfolio_id: set(venture_ids)},
        )
        self._closed = False
        self._seed_registry()

    def _seed_registry(self) -> None:
        self.registry.create_portfolio(build_portfolio(
            portfolio_id=self.portfolio_id,
            name="P6.5 Synthetic Portfolio",
            policy_version="p6.0",
            configuration_fingerprint=self.configuration_fingerprint,
            actor={"actor_id": "p6.5-harness", "role": "system"},
            correlation_id="p65-portfolio-correlation",
            idempotency_key="p65-portfolio",
            created_at=self.timestamp,
        ))
        for index, venture_id in enumerate(self.venture_ids, start=1):
            self.registry.add_membership(build_membership(
                portfolio_id=self.portfolio_id,
                venture_id=venture_id,
                venture_scope={"portfolio_id": self.portfolio_id, "venture_id": venture_id},
                policy_version="p6.0",
                configuration_fingerprint=self.configuration_fingerprint,
                actor={"actor_id": "p6.5-harness", "role": "system"},
                correlation_id=f"p65-membership-{index}",
                idempotency_key=f"p65-membership-{index}",
                private_metadata={"private_marker": f"private-{venture_id}"},
                created_at=self.timestamp,
            ))

    def _packet(self, venture_id: str, index: int) -> dict[str, Any]:
        return build_coordination_packet(
            portfolio_id=self.portfolio_id,
            venture_id=venture_id,
            sender_actor={"actor_id": "p65-ceo", "role": "portfolio-ceo"},
            recipient_actor={"actor_id": f"manager-{venture_id}", "role": "venture-manager"},
            sender_role="portfolio-ceo",
            recipient_role="venture-manager",
            request_id=f"p65-request-{index}",
            correlation_id=f"p65-correlation-{index}",
            task_id=f"p65-task-{index}",
            scope={"portfolio_id": self.portfolio_id, "venture_id": venture_id},
            capability_envelope={"capabilities": ["shared-service-demand"]},
            originating_capability_envelope={"capabilities": ["shared-service-demand"]},
            policy_version="p6.1",
            configuration_fingerprint=self.configuration_fingerprint,
            source_ids=["p6.4-accepted"],
            source_hashes=["a" * 64],
            lineage=["p6.4-accepted"],
            taint=[],
            created_at=self.timestamp,
            expiry_at=self.expiry,
        )

    def _demand(self, venture_id: str, index: int) -> dict[str, Any]:
        return build_demand(
            demand_id="p65-shared-demand",
            portfolio_id=self.portfolio_id,
            venture_id=venture_id,
            coordination_request_id=f"p65-request-{index}",
            requester_actor={"actor_id": f"manager-{venture_id}", "role": "venture-manager"},
            service_class="metadata-read",
            requested_units=2,
            policy_version="p6.2",
            configuration_fingerprint=self.configuration_fingerprint,
            created_at=self.timestamp,
            expiry_at=self.expiry,
            source_ids=[f"p65-request-{index}"],
            source_hashes=["b" * 64],
            lineage=[f"p6.1-p65-request-{index}"],
            taint=[],
            quota_max_units=10,
        )

    def run(self) -> dict[str, Any]:
        packets = []
        demands = []
        outputs = []
        for index, venture_id in enumerate(self.venture_ids, start=1):
            packet = self._packet(venture_id, index)
            packets.append(self.coordination.submit(packet))
            demand = self._demand(venture_id, index)
            demands.append(demand)
            outputs.append(self.shared_service.run(demand))

        analysis_records = []
        for output in outputs:
            analysis_records.append({
                "record_id": output["output_id"],
                "demand_id": output["demand_id"],
                "portfolio_id": output["portfolio_id"],
                "venture_id": output["venture_id"],
                "coordination_request_id": output["coordination_request_id"],
                "service_class": output["service_class"],
                "requested_units": output["requested_units"],
                "quota_max_units": 10,
                "aggregate_quota_minor": 10,
                "created_at": self.timestamp,
                "expiry_at": self.expiry,
                "configuration_fingerprint": self.configuration_fingerprint,
                "source_ids": list(output["source_ids"]),
                "source_hashes": list(output["source_hashes"]),
                "lineage": list(output["lineage"]),
                "taint": list(output["taint"]),
                "synthetic_only": True,
                "effect": "none",
            })
        analysis_request = build_analysis_request(
            analysis_id="p65-analysis",
            portfolio_id=self.portfolio_id,
            records=analysis_records,
            policy_version="p6.3",
            configuration_fingerprint=self.configuration_fingerprint,
            source_ids=[item["output_id"] for item in outputs],
            source_hashes=[item["output_hash"] for item in outputs],
            lineage=["p6.2-shared-service"],
            taint=[],
            analyzed_at=self.timestamp,
        )
        analysis = self.analyzer.analyze(analysis_request)
        leakage = next(
            (item for item in analysis["findings"] if item["code"] == "CROSS_VENTURE_LEAKAGE"),
            None,
        )
        if leakage is None:
            raise PortfolioCertificationDenied("P6.5 expected cross-venture leakage finding")
        op_common = {
            "portfolio_id": self.portfolio_id,
            "venture_id": self.venture_ids[0],
            "policy_version": "p6.4",
            "configuration_fingerprint": self.configuration_fingerprint,
            "actor": {"actor_id": "p65-reviewer", "role": "reviewer"},
            "source_ids": leakage["source_record_ids"],
            "source_hashes": leakage["source_hashes"],
            "lineage": [analysis["result_hash"]],
            "taint": leakage["taint"],
            "created_at": self.timestamp,
            "reason": "P6.5 synthetic anomaly quarantine",
        }
        quarantine, _ = self.operations.quarantine(build_operation(
            action_id="p65-quarantine-venture-a",
            operation="quarantine",
            correlation_id="p65-quarantine-correlation",
            idempotency_key="p65-quarantine",
            **op_common,
        ))
        recovery, _ = self.operations.recover(build_operation(
            action_id="p65-recover-venture-a",
            operation="recover",
            correlation_id="p65-recover-correlation",
            idempotency_key="p65-recover",
            **op_common,
        ))
        harvest, _ = self.operations.harvest(build_operation(
            action_id="p65-harvest-venture-b",
            operation="harvest",
            portfolio_id=self.portfolio_id,
            venture_id=self.venture_ids[1],
            policy_version="p6.4",
            configuration_fingerprint=self.configuration_fingerprint,
            actor={"actor_id": "p65-reviewer", "role": "reviewer"},
            correlation_id="p65-harvest-correlation",
            idempotency_key="p65-harvest",
            source_ids=[outputs[1]["output_id"]],
            source_hashes=[outputs[1]["output_hash"]],
            lineage=[analysis["result_hash"]],
            taint=[],
            created_at=self.timestamp,
            reason="P6.5 synthetic harvest record",
            harvested_units=2,
        ))
        reinvestment, _ = self.operations.propose_reinvestment(build_operation(
            action_id="p65-reinvest-venture-b",
            operation="reinvestment-proposal",
            portfolio_id=self.portfolio_id,
            venture_id=self.venture_ids[1],
            policy_version="p6.4",
            configuration_fingerprint=self.configuration_fingerprint,
            actor={"actor_id": "p65-reviewer", "role": "reviewer"},
            correlation_id="p65-reinvest-correlation",
            idempotency_key="p65-reinvest",
            source_ids=[harvest["action_id"]],
            source_hashes=[harvest["record_hash"]],
            lineage=[harvest["record_hash"]],
            taint=[],
            created_at=self.timestamp,
            reason="P6.5 synthetic reinvestment proposal",
            proposed_units=1,
        ))
        report = {
            "portfolio_view": self.registry.aggregate_view(self.portfolio_id),
            "coordination": packets,
            "demands": demands,
            "shared_service_outputs": outputs,
            "analysis": analysis,
            "operations": [quarantine, recovery, harvest, reinvestment],
            "live_authority_fields": {field: False for field in LIVE_FIELDS},
            "synthetic_only": True,
            "effect": "none",
            "external_action": False,
            "capability_granted": False,
            "execution_requested": False,
            "private_metadata_exposed": False,
        }
        report["report_hash"] = digest(canonical(report))
        return report

    def close(self) -> None:
        if not self._closed:
            self.operations.close()
            self.coordination.close()
            self.registry.close()
            self._closed = True
