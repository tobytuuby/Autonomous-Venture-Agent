"""Local infrastructure evidence only; no provider inference or remote staging."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "ventures/venture-001/runtime"
sys.path.insert(0, str(RUNTIME))
import online_checks as online
import provider_manager as pm
import test_provider_manager as fixtures

class OnlineBoundaryTests(unittest.TestCase):
    def test_backend_source_is_bounded_and_tests_stay_role_separate(self):
        files = {"app.py": "def application(e,s): return []",
                 "backend/store.py": "import sqlite3", "backend/schema.sql": "CREATE TABLE x(id);"}
        self.assertEqual(pm.file_map(files, "development"), files)
        for name in ("checks.py", "other.py", "run.sh", "backend/../escape.py",
                     "/tmp/app.py", "backend/secret.env", "requirements.txt"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                pm.file_map({name: "x"}, "development")

    def test_only_literal_same_origin_api_fetch_is_newly_permitted(self):
        self.assertFalse(pm.external_communication_denied(
            'fetch("/api/items", {method: "POST"})', online=True))
        self.assertTrue(pm.external_communication_denied('fetch("/api/items")'))
        for source in ('fetch(url)', 'fetch("//example.invalid/x")',
                       'fetch("http://127.0.0.1:8200/v1")',
                       'fetch("/api/items" + target)', 'new WebSocket("/api/items")',
                       'new XMLHttpRequest()', '<script src="//example.invalid/x"></script>',
                       '<form action="/api/items" method="post"></form>'):
            with self.subTest(source=source):
                self.assertTrue(pm.external_communication_denied(source, online=True))

    def test_versioned_requirements_bind_online_acceptance_and_owner_hold(self):
        body = pm.REQUIREMENTS.read_text()
        for text in ("server-side inventory", "localStorage-only", "UNAPPROVED PILOT",
                     "/api/restore", "/api/account", "/api/recover", "backup deletion lag",
                     "second independent browser", "pricing", "Origin", "/49"):
            self.assertIn(text, body)
        self.assertIn("ONLINE", pm.OBJECTIVE)
        self.assertTrue(all(v is False for v in pm.DENIED.values()))

    def test_existing_delegation_fixture_cannot_claim_online_acceptance(self):
        import uuid
        with pm.AgentManager("online-test-" + uuid.uuid4().hex[:24],
                             test_provider=fixtures.TestProvider()) as manager:
            try:
                result = manager.run_agents()
                self.assertEqual(result["status"], "prepared_with_research_blocked")
                self.assertEqual(result["online_acceptance"], "NOT_VERIFIED_TEST_ADAPTER")
                self.assertEqual(result["evidence_class"], "test_adapter_only")
                self.assertEqual({t["role"] for t in result["tasks"]}, set(pm.ROLES))
                self.assertIn("app.py", manager.development_files())
                request = json.loads((manager.home / "inference/development-1/request.json").read_text())
                self.assertIn("backend", request["system"])
                self.assertIn(pm.REQUIREMENTS.name, request["opportunity"]["payload"]["inputs"])
            finally:
                shutil.rmtree(manager.home)

    def test_static_worker_cannot_pass_development_admission(self):
        import uuid
        original = fixtures.TestProvider()
        def respond(request, schemas):
            result = original(request, schemas)
            if request["opportunity"]["task_id"] == "development-1":
                answer = json.loads(result["decision"]["content"])
                del answer["files"]["app.py"]
                answer["files"]["index.html"] += "<script>localStorage.setItem('stock','[]')</script>"
                result["decision"]["content"] = json.dumps(answer)
            return result
        with pm.AgentManager("online-test-" + uuid.uuid4().hex[:24], test_provider=respond) as manager:
            try:
                manager.plan()
                manager.dispatch_agent(next(t for t in manager.tasks() if t["role"] == "development"))
                dev = manager.effective("development-1")
                self.assertEqual(dev["status"], "rejected")
                self.assertIn("online backend", dev["record"]["defects"][0])
                self.assertFalse(manager.development_files())
            finally:
                shutil.rmtree(manager.home)

    def test_static_localstorage_product_is_rejected_by_real_http_gate(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as home:
            root = Path(home)
            source = root / "source"
            source.mkdir()
            (source / "index.html").write_text("<script>localStorage.setItem('inventory','[]')</script>")
            # A nominal backend cannot turn an offline product into an online app.
            (source / "app.py").write_text(
                "def application(env, start):\n"
                "    start('200 OK', [('Content-Type','text/html')])\n"
                "    return [b'<html>static offline inventory</html>']\n")
            with online.private_server(source, root / "output") as port:
                with self.assertRaisesRegex(AssertionError, "/api/items returned 200"):
                    online.acceptance(port)

    def test_http_adapter_runs_backend_with_durable_state_and_containment(self):
        # Purpose-built probe, not a product. Real HTTP requests, separate backend
        # processes, writable state, denied filesystem/network/child operations.
        probe = '''import json, socket, subprocess
from pathlib import Path
def application(env, start):
    for action in (lambda: Path('/etc/passwd').read_text(),
                   lambda: socket.socket(),
                   lambda: subprocess.run(['/usr/bin/true'])):
        try:
            action()
        except (OSError, PermissionError):
            continue
        raise AssertionError('containment failed')
    p = Path(env['STUDIO_DATA_DIR']) / 'counter'
    n = int(p.read_text()) + 1 if p.exists() else 1
    p.write_text(str(n))
    start('200 OK', [('Content-Type', 'application/json')])
    return [json.dumps({'count': n}).encode()]
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as home:
            root = Path(home)
            source = root / "source"
            source.mkdir()
            (source / "app.py").write_text(probe)
            (source / "index.html").write_text("<title>Probe only</title>")
            with online.private_server(source, root / "output") as port:
                for count in (1, 2):
                    status, body, _ = online.Client(port).request("GET", "/api/probe")
                    self.assertEqual(status, 200)
                    self.assertEqual(json.loads(body), {"count": count})
                status, _, _ = online.Client(port).request("GET", "/app.py")
                self.assertEqual(status, 404)

    def test_no_backend_and_symlink_sources_fail_closed(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as home:
            root = Path(home)
            source = root / "source"
            source.mkdir()
            with self.assertRaises(ValueError), online.private_server(source, root / "output"):
                pass
            (source / "app.py").write_text("x")
            (source / "escape").symlink_to(ROOT / "AGENTS.md")
            with self.assertRaises(ValueError), online.private_server(source, root / "output2"):
                pass

if __name__ == "__main__":
    unittest.main()
