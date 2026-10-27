"""Run supplemental signed scenarios and retain raw journals, never private keys."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from agents.ceo.escalation_inbox import EscalationInbox
from agents.ceo.preparation_broker import PreparationBroker
from tests.test_preparation_broker import PreparationBrokerTests

OUTPUT = ROOT / "artifacts/milestone1-evidence/scenarios"
OUTPUT.mkdir(parents=True, exist_ok=True)
events, actors, reports = [], [], []
original_save = EscalationInbox._save
original_init = PreparationBroker.__init__


def save(self, item, kind):
    result = original_save(self, item, kind)
    events.append(dict(journal=type(self).__name__, kind=kind,
                       snapshot=json.loads(json.dumps(item))))
    return result


def init(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    actors.append(self.identities.public_manifest())


class EvidenceResult(unittest.TextTestResult):
    def startTest(self, test):
        events.clear()
        actors.clear()
        super().startTest(test)

    def stopTest(self, test):
        failed = any(t == test for t, _ in self.failures + self.errors)
        report = dict(scenario=test.id(), result="FAIL" if failed else "PASS",
            classification="SUPPLEMENTAL_LOCAL_SYNTHETIC_NO_PROVIDER",
            public_actor_manifests=actors.copy(), raw_events=events.copy())
        name = test.id().split(".")[-1] + ".json"
        (OUTPUT / name).write_text(json.dumps(report, indent=2) + "\n")
        reports.append(dict(scenario=test.id(), result=report["result"], artifact=name))
        super().stopTest(test)


with patch.object(EscalationInbox, "_save", save), patch.object(PreparationBroker, "__init__", init):
    result = unittest.TextTestRunner(verbosity=2, resultclass=EvidenceResult).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(PreparationBrokerTests))
(OUTPUT / "decision-log.json").write_text(json.dumps(dict(
    command="PYTHONDONTWRITEBYTECODE=1 python3 tests/certification/milestone1-20261027/run_scenarios.py",
    tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
    classification="SUPPLEMENTAL_LOCAL_SYNTHETIC_NO_PROVIDER",
    adv_universe="ADV-001–ADV-049 /49 unchanged", scenarios=reports), indent=2) + "\n")
raise SystemExit(not result.wasSuccessful())
