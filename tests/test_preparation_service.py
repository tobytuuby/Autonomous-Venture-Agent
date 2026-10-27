"""Offline installation contract; no signing fixtures or provider calls."""
import json
from pathlib import Path
import tempfile
import unittest

from agents.ceo.control_plane import ControlPlane, tick, load_trust
from agents.ceo.escalation_inbox import ROOT, canonical


class PreparationServiceTests(unittest.TestCase):
    def test_empty_trust_spool_replay_denial_and_restart(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as temp:
            base = Path(temp)
            base.chmod(0o700)
            trust = base / "trust.json"
            trust.write_text('{"actors":{}}')
            trust.chmod(0o400)
            requests = base / "requests"
            requests.mkdir(mode=0o700)
            request = dict(operation="ingest", body=dict(item_id="test-intake",
                venture_id="test-venture", source="TEST-ONLY", packet="Test packet"))
            (requests / "001.json").write_text(canonical(request))
            control = ControlPlane(base, actors=load_trust(trust))
            try:
                self.assertEqual(tick(control, requests)["outcomes"][0]["status"], "RECORDED")
                first = control.inbox.read("test-intake")
                self.assertEqual(tick(control, requests)["outcomes"][0]["status"], "RECORDED")
                self.assertEqual(control.inbox.read("test-intake"), first)
            finally:
                control.close()
            control = ControlPlane(base, actors=load_trust(trust))
            try:
                self.assertEqual(control.inbox.read("test-intake"), first)
                for operation in ("decision", "create", "worker", "payment", "launch",
                                  "provider", "execute", "enroll"):
                    (requests / "002.json").write_text(canonical(dict(operation=operation, body={})))
                    self.assertEqual(tick(control, requests)["outcomes"][1]["status"], "DENIED")
                    self.assertEqual(control.workflow.read(), [])
                    self.assertIsNone(control.inbox.read("test-intake")["decision"])
                self.assertFalse(control.status()["operational_authority"])
            finally:
                control.close()

    def test_unit_excludes_protected_inbox_credentials_and_network(self):
        unit = (ROOT / "infrastructure/systemd/venture-preparation-control.service").read_text()
        for setting in ("User=venture-ceo", "PrivateNetwork=true", "ProtectSystem=strict",
                        "NoNewPrivileges=true", "IPAddressDeny=any", "RestrictNamespaces=true"):
            self.assertIn(setting, unit.splitlines())
        blocked = next(line for line in unit.splitlines() if line.startswith("InaccessiblePaths="))
        for path in ("artifacts/scheduled-ceo", "/etc/venture-ceo.env",
                     "/etc/venture-ceo-shadow.env", "/var/lib/venture-ceo", "/run"):
            self.assertIn(path, blocked)
        self.assertNotIn("--inbox-database", unit)
        self.assertNotIn("EnvironmentFile=", unit)
        timer = (ROOT / "infrastructure/systemd/venture-preparation-control.timer").read_text()
        self.assertIn("OnUnitActiveSec=1h", timer)
        self.assertIn("WantedBy=timers.target", timer)
