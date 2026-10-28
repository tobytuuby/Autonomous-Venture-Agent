"""Test adapters only; none of these results count as genuine inference."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from provider_manager import AgentManager, validate_plan, file_map, ROLES, DENIED, CAPABILITIES, external_communication_denied
from agents.ceo.provider import ModelProviderError, OpenAICompatibleShadowModel
from agents.ceo.gates import CertificationGateError

def plan(reverse=False):
    roles = list(reversed(ROLES)) if reverse else list(ROLES)
    return {"tasks": [{"role": role, "instruction": "Prepare bounded " + role + " deliverables",
                       "depends_on": ["development"] if role in ("testing", "security") else []}
                      for role in roles]}

class TestProvider:
    def __init__(self, *, invalid_dev=False, fail_checks=False, reverse=False, tamper_hash=False, security_findings=None):
        self.calls = []
        self.requests = []
        self.invalid_dev, self.fail_checks = invalid_dev, fail_checks
        self.fail_first_testing = False
        self.reverse, self.tamper_hash = reverse, tamper_hash
        self.security_findings = security_findings or []

    def __call__(self, request, schemas):
        assert schemas == ()
        opportunity = request["opportunity"]
        identity = opportunity["task_id"]
        self.calls.append(copy.deepcopy(opportunity))
        self.requests.append(copy.deepcopy(request))
        if identity == "manager-plan":
            answer = plan(self.reverse)
        elif identity.startswith("manager-"):
            answer = {"instruction": "Correct the recorded failure with bounded source remediation"}
        else:
            role = identity.rsplit("-", 1)[0]
            answer = {"task_id": identity, "status": "ok", "files": {}, "evidence": {}}
            if role == "development":
                answer["files"] = {"index.html": "<!doctype html><title>Kit</title><main>Restock app</main>",
                                   "README.md": "UNAPPROVED PILOT. Trusted online_checks.py 127.0.0.1 preview; recovery/privacy draft",
                                   "app.py": "def application(environ, start_response):\n    start_response('501 Not Implemented', [])\n    return [b'contract fixture only']\n"}
                if self.invalid_dev and identity.endswith("-1"):
                    del answer["files"]["index.html"]
            if role in ("testing", "security"):
                answer["evidence"]["inspected_hashes"] = opportunity["payload"]["app_hashes"]
                if self.tamper_hash:
                    answer["evidence"]["inspected_hashes"] = {"index.html": "0" * 64}
            if role == "testing":
                answer["files"]["checks.py"] = (
                    "import sys\nfrom pathlib import Path\n"
                    "body=(Path(sys.argv[1])/'index.html').read_text()\n"
                    "assert 'Restock app' in body\nprint('actual generated source checked')\n")
                if self.fail_checks:
                    answer["files"]["checks.py"] += "raise AssertionError('injected real failure')\n"
                if self.fail_first_testing and identity == "testing-1":
                    answer["files"]["checks.py"] += "raise AssertionError('actionable correction evidence')\n"
            if role == "security":
                answer["files"]["security.md"] = "Bounded test inspection; no certification"
                answer["evidence"]["findings"] = copy.deepcopy(self.security_findings.get(identity, [])) if isinstance(self.security_findings, dict) else copy.deepcopy(self.security_findings)
            if role == "research":
                answer.update(status="policy_blocked")
                answer["evidence"] = {"sources": [], "claims": [], "reason": "No approved source-bound GET tool"}
            if role == "commercial":
                answer["files"]["collateral.md"] = "Draft: Restock your studio. Pricing undecided. Demand unverified."
                answer["evidence"] = {"pricing_status": "undecided", "demand_verified": False, "publication_authorized": False}
        return {"decision": {"content": json.dumps(answer)}, "tool_call": None}

class AgentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.provider = TestProvider()
        self.name = "ai-test-" + uuid.uuid4().hex
        self.manager = AgentManager(self.name, test_provider=self.provider)

    def tearDown(self):
        self.manager.close()
        shutil.rmtree(self.manager.home)

    def test_dynamic_plan_distinct_worker_calls_and_actual_checks(self):
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "prepared_with_research_blocked")
        self.assertEqual([x["task_id"] for x in self.provider.calls][0], "manager-plan")
        self.assertEqual(len(self.provider.calls), 6)
        self.assertEqual({t["role"] for t in result["tasks"]}, set(ROLES))
        testing = next(t for t in result["tasks"] if t["role"] == "testing")
        self.assertEqual(testing["record"]["execution"]["exit_status"], 0)
        self.assertEqual(testing["record"]["execution"]["browser"]["status"], "test_adapter_skipped")
        self.assertNotIn("browser-checks.log", str(testing["record"]["artifacts"]))
        self.assertIn("actual generated source checked",
                      (self.manager.home / testing["record"]["execution"]["log"]).read_text())
        self.assertTrue((self.manager.home / "hosted-app/index.html").is_file())
        self.assertEqual(result["evidence_class"], "test_adapter_only")
        self.assertEqual(result["online_acceptance"], "NOT_VERIFIED_TEST_ADAPTER")
        self.assertTrue(all(not t["record"]["agent_inference"] for t in result["tasks"]))
        self.assertTrue(all(v is False for v in result["authorities"].values()))

    def test_dialog_form_permitted_and_reviews_dispatched(self):
        original = self.provider.__call__
        def respond(request, schemas):
            result = original(request, schemas)
            if request["opportunity"]["task_id"] == "development-1":
                answer = json.loads(result["decision"]["content"])
                answer["files"]["index.html"] += (
                    '<dialog><form method="dialog"><button>Confirm</button></form></dialog>')
                result["decision"]["content"] = json.dumps(answer)
            return result
        self.manager.test_provider = respond
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "prepared_with_research_blocked")
        for role in ("development", "testing", "security"):
            task = self.manager.effective(role + "-1")
            self.assertEqual(task["status"], "accepted")
            self.assertEqual(task["attempt"], 1)

    def test_static_dialog_form_attribute_variants_permitted(self):
        for source in ('<form method="dialog"></form>', "<form method='dialog'></form>",
                       '<FORM METHOD=DiAlOg></FORM>'):
            with self.subTest(source=source):
                self.assertFalse(external_communication_denied(source))

    def test_static_external_communication_denied(self):
        for source in (
            '<form method="post"></form>', '<form></form>', '<form method="get"></form>',
            '<form action="/submit"></form>', '<form method="dialog" action="/submit"></form>',
            '<form method="dialog" method="post"></form>', '<form method="dialog"',
            '<form method="dialog"><button formmethod="post">Send</button></form>',
            '<form method="dialog"><button formaction="/submit">Send</button></form>',
            '<form method="dialog"></form><form method="post"></form>',
            '<a href="https://example.com">Link</a>', '<script>fetch("/send")</script>',
            '<script>new XMLHttpRequest()</script>', '<script>new WebSocket("/socket")</script>',
        ):
            with self.subTest(source=source):
                self.assertTrue(external_communication_denied(source))

    def test_manager_plan_changes_dispatch_order(self):
        self.provider.reverse = True
        self.manager.run_agents()
        identities = [x["task_id"] for x in self.provider.calls]
        self.assertEqual(identities[1], "commercial-1")
        self.assertLess(identities.index("development-1"), identities.index("testing-1"))

    def test_restart_does_not_replay_accepted_inference(self):
        self.manager.run_agents()
        count = len(self.provider.calls)
        self.manager.close()
        self.manager = AgentManager(self.name, test_provider=self.provider)
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "prepared_with_research_blocked")
        self.assertEqual(len(self.provider.calls), count)

    def test_manager_commissions_source_correction(self):
        self.provider.invalid_dev = True
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "prepared_with_research_blocked")
        tasks = {t["id"]: t for t in result["tasks"]}
        self.assertEqual(tasks["development-1"]["status"], "rejected")
        self.assertEqual(tasks["development-2"]["status"], "accepted")
        correction = next(x for x in self.provider.calls if x["task_id"] == "development-2")
        self.assertIn("prior_response", correction["payload"])
        self.assertIn("correction", correction["payload"])
        self.assertIn("manager-development-2", [x["task_id"] for x in self.provider.calls])

    def test_development_correction_preserves_role_boundary_and_manager_product_requirements(self):
        conflict = "Return Python-standard-library checks in checks.py plus security/research/commercial artifacts."
        requests = {}
        original = self.provider.__call__

        def respond(request, schemas):
            identity = request["opportunity"]["task_id"]
            requests[identity] = copy.deepcopy(request)
            result = original(request, schemas)
            answer = json.loads(result["decision"]["content"])
            if identity == "manager-plan":
                next(t for t in answer["tasks"] if t["role"] == "development")["instruction"] = conflict
            elif identity == "manager-development-2":
                answer["instruction"] = conflict
            elif identity == "development-1":
                answer["files"]["checks.py"] = "print('wrong role')"
            result["decision"]["content"] = json.dumps(answer)
            return result

        self.manager.test_provider = respond
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "prepared_with_research_blocked")
        first = next(t for t in result["tasks"] if t["id"] == "development-1")
        self.assertIn("artifact path/type denied", first["record"]["defects"][0])
        corrected = self.manager.effective("development-1")
        self.assertEqual((corrected["id"], corrected["correction_of"], corrected["status"]),
                         ("development-2", "development-1", "accepted"))
        payload = requests["development-2"]["opportunity"]["payload"]
        self.assertTrue(payload["instruction"].startswith(conflict))
        self.assertEqual(payload["correction"]["instruction"], conflict)
        self.assertIn("checks.py", payload["prior_response"]["files"])
        for identity in ("development-1", "development-2"):
            with self.subTest(identity=identity):
                system = requests[identity]["system"]
                self.assertIn("ROLE: development", system)
                self.assertIn("Functional authenticated ONLINE app", system)
                self.assertIn("Durable server-side tenant inventory", system)
                self.assertIn("exact HTTP API", system)
                self.assertIn("recovery/backup/deletion/privacy", system)
                self.assertIn("The hosted site root is index.html", requests[identity]["opportunity"]["payload"]["instruction"])
                self.assertIn("never static/localStorage-only inventory", requests[identity]["opportunity"]["payload"]["instruction"])
                self.assertIn("optional backend/*.py, backend/*.sql", system)
                self.assertIn("Never return test scripts, checks.py", system)
                self.assertIn("security/research/commercial artifacts or other role outputs", system)
                self.assertIn("Follow the manager's task-specific product requirements and correction instructions", system)
                self.assertIn("within this development role boundary", system)
                self.assertIn("If a manager instruction requests another role's artifacts or execution", system)
                self.assertIn("Tests belong to the separate testing specialist", system)
        security_system = requests["security-1"]["system"]
        self.assertIn("Return exactly one file named security.md", security_system)
        self.assertIn("Do not return scripts, executable files, or other artifacts", security_system)

    def test_corrections_through_four_require_rejection_and_stay_role_bound_after_restart(self):
        m = self.manager
        m.plan()
        first = next(t for t in m.tasks() if t["id"] == "research-1")
        m.update(first, "rejected", {"defects": ["synthetic first failure"]})
        m.assign_agent("research", [], "research-1")
        for attempt in (2, 3, 4, 5):
            current = m.effective("research-1")
            self.assertEqual((current["id"], current["role"], current["attempt"], current["correction_of"]),
                             (f"research-{attempt}", "research", attempt, f"research-{attempt - 1}"))
            for status in ("pending", "running", "accepted"):
                m.update(current, status, {"artifacts": []})
                with self.subTest(attempt=attempt, status=status), self.assertRaises(ValueError):
                    m.assign_agent("research", [], current["id"])
            if attempt == 5:
                m.update(current, "pending", {"artifacts": []})
                m.dispatch_agent(m.effective("research-1"))
                request = next(c for c in self.provider.calls if c["task_id"] == "research-5")
                self.assertEqual(request["payload"]["prior_failure"]["defects"],
                                 ["synthetic correction failure"])
                break
            m.update(current, "rejected", {"defects": ["synthetic correction failure"]})
            m.close()
            self.manager = m = AgentManager(self.name, test_provider=self.provider)
            with self.assertRaises(ValueError):
                m.assign_agent("commercial", [], current["id"])
            with self.assertRaises(ValueError):
                m.assign_agent("research", ["development-1"], current["id"])
            m.assign_agent("research", [], current["id"])
        self.assertEqual(m.effective("research-1")["status"], "accepted")
        count = len(self.provider.calls)
        m.close()
        self.manager = m = AgentManager(self.name, test_provider=self.provider)
        m.plan()
        self.assertEqual(m.effective("research-1")["id"], "research-5")
        self.assertEqual(len(self.provider.calls), count)
        with self.assertRaises(PermissionError):
            m.dispatch_agent(m.effective("research-1"))

    def test_correction_chain_can_exceed_six_attempts_within_run_budget(self):
        m = self.manager
        m.plan()
        for _ in range(7):
            current = m.effective("research-1")
            m.update(current, "rejected", {"defects": ["bounded synthetic failure"]})
            m.assign_agent("research", [], current["id"])
        self.assertEqual(m.effective("research-1")["attempt"], 8)
        self.assertLessEqual(len(m.tasks()), CAPABILITIES["max_tasks"])
        self.assertNotIn("max_attempts_per_role", CAPABILITIES)

    def test_failure_logs_reach_manager_and_worker_corrections(self):
        self.provider.fail_first_testing = True
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "prepared_with_research_blocked")
        requests = {r["opportunity"]["task_id"]: r for r in self.provider.requests}
        for identity in ("manager-development-2", "development-2", "manager-testing-2", "testing-2"):
            self.assertIn(identity, requests)
            payload = requests[identity]["opportunity"]["payload"]
            logs = payload["prior_failure_logs"]
            check_log = next(x for x in logs if x["task_id"] == "testing-1" and x["path"] == "testing-1/checks.log" and x["stage"] == "checks")
            self.assertTrue(check_log["verified"])
            self.assertIn("actionable correction evidence", check_log["excerpt"])
            self.assertLessEqual(len(check_log["excerpt"].encode()), 12000)
        self.assertEqual(result["budget"]["tasks_limit"], 25)
        self.assertEqual(result["budget"]["calls_limit"], 46)
        self.assertFalse(result["budget"]["task_budget_exhausted"])

    def test_all_roles_can_use_run_wide_budget_of_twenty_five_tasks(self):
        original = self.provider.__call__
        def respond(request, schemas):
            result = original(request, schemas)
            identity = request["opportunity"]["task_id"]
            if not identity.startswith("manager-") and not identity.endswith("-5"):
                answer = json.loads(result["decision"]["content"])
                answer["status"] = "failed"
                result["decision"]["content"] = json.dumps(answer)
            return result
        self.manager.test_provider = respond
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "prepared_with_research_blocked")
        self.assertEqual(len(result["tasks"]), 25)
        self.assertEqual(len(result["calls"]), 46)
        self.assertEqual(len({c["id"] for c in result["calls"]}), 46)
        self.assertEqual(result["capabilities"]["max_tasks"], 25)
        self.assertNotIn("max_attempts_per_role", result["capabilities"])
        self.assertEqual(result["capabilities"]["max_inference_calls"], 46)
        self.assertTrue(result["budget"]["tasks_used"] <= result["budget"]["tasks_limit"])
        for role in ROLES:
            tasks = [t for t in result["tasks"] if t["role"] == role]
            self.assertEqual([t["status"] for t in tasks], ["rejected", "rejected", "rejected", "rejected", "accepted"])
            self.assertEqual([t["correction_of"] for t in tasks], [None, role + "-1", role + "-2", role + "-3", role + "-4"])
            self.manager.update(tasks[-1], "rejected", {"defects": ["final synthetic failure"]})
            with self.assertRaises(ValueError):
                self.manager.assign_agent(role, tasks[-1]["deps"], role + "-5")
            self.assertFalse(any(t["id"] == role + "-6" for t in self.manager.tasks()))
        count = len(self.provider.calls)
        self.manager.close()
        self.manager = AgentManager(self.name, test_provider=respond)
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(len(result["tasks"]), 25)
        self.assertEqual(len(self.provider.calls), count)
        self.assertTrue(all(v is False for v in result["authorities"].values()))

    def test_third_application_correction_invalidates_reviews_and_dependency_versions(self):
        self.provider.reverse = True
        original = self.provider.__call__
        def respond(request, schemas):
            result = original(request, schemas)
            identity = request["opportunity"]["task_id"]
            if identity in ("testing-1", "testing-2", "testing-3"):
                answer = json.loads(result["decision"]["content"])
                answer["files"]["checks.py"] += "raise AssertionError('synthetic application defect')\\n"
                result["decision"]["content"] = json.dumps(answer)
            return result
        self.manager.test_provider = respond
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "prepared_with_research_blocked")
        self.assertEqual(self.manager.effective("development-1")["id"], "development-4")
        for role in ("testing", "security"):
            effective = self.manager.effective(role + "-1")
            self.assertEqual(effective["id"], role + "-4")
            self.assertEqual(effective["record"]["dependency_versions"]["development-1"]["id"], "development-4")
            prior = [t for t in result["tasks"] if t["role"] == role and t["attempt"] < 4]
            self.assertTrue(all(t["status"] == "rejected" for t in prior))
        security = [t for t in result["tasks"] if t["role"] == "security" and t["attempt"] < 4]
        self.assertTrue(all("invalidated" in t["record"]["defects"][0] for t in security))
        count = len(self.provider.calls)
        self.manager.close()
        self.manager = AgentManager(self.name, test_provider=respond)
        self.assertEqual(self.manager.run_agents()["status"], "prepared_with_research_blocked")
        self.assertEqual(len(self.provider.calls), count)

    def test_interrupted_third_correction_inference_is_never_replayed(self):
        m = self.manager
        m.plan()
        for identity in ("research-1", "research-2", "research-3"):
            task = next(t for t in m.tasks() if t["id"] == identity)
            m.update(task, "rejected", {"defects": ["synthetic failure"]})
            m.assign_agent("research", [], identity)
        fourth = m.effective("research-1")
        m.update(fourth, "running", {"started": "synthetic interruption"})
        m.save("calls", m.meta("calls") + [{"id": "manager-research-4", "status": "running"}])
        count = len(self.provider.calls)
        m.close()
        self.manager = AgentManager(self.name, test_provider=self.provider)
        self.assertEqual(self.manager.run_agents()["status"], "blocked")
        self.assertEqual(len(self.provider.calls), count)

    def test_security_report_accepts_nonblocking_findings_for_owner_review(self):
        self.provider.security_findings = [{"severity": "medium", "title": "Residual local data exposure", "file": "index.html", "defect": "Local data is visible to same-origin scripts."}]
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "prepared_with_research_blocked")
        security = self.manager.effective("security-1")
        self.assertEqual(security["status"], "accepted")
        self.assertEqual(security["record"]["evidence"]["findings"][0]["severity"], "medium")

    def test_failed_security_worker_does_not_reject_the_application(self):
        self.provider.security_findings = [{"severity": "medium", "title": "Unverified finding", "file": "index.html", "defect": "Unverified current-source issue."}]
        original = self.provider.__call__

        def respond(request, schemas):
            result = original(request, schemas)
            if request["opportunity"]["task_id"] == "security-1":
                answer = json.loads(result["decision"]["content"])
                answer["status"] = "failed"
                result["decision"]["content"] = json.dumps(answer)
            return result

        self.manager.test_provider = respond
        result = self.manager.run_agents()
        security1 = next(t for t in result["tasks"] if t["id"] == "security-1")
        development1 = next(t for t in result["tasks"] if t["id"] == "development-1")
        security2 = next(t for t in result["tasks"] if t["id"] == "security-2")
        self.assertEqual(security1["status"], "rejected")
        self.assertTrue(any("worker reported failure" in defect for defect in security1["record"]["defects"]))
        self.assertEqual(development1["status"], "accepted")
        self.assertEqual(security2["status"], "accepted")

    def test_out_of_scope_security_finding_does_not_reject_application(self):
        original = self.provider.__call__

        def respond(request, schemas):
            result = original(request, schemas)
            if request["opportunity"]["task_id"] == "security-1":
                answer = json.loads(result["decision"]["content"])
                answer["evidence"]["findings"] = [{
                    "severity": "high", "title": "Test harness concern",
                    "file": "validation/test-restock.js",
                    "defect": "The validation harness uses an isolated JavaScript VM."
                }]
                result["decision"]["content"] = json.dumps(answer)
            return result

        self.manager.test_provider = respond
        result = self.manager.run_agents()
        security1 = next(t for t in result["tasks"] if t["id"] == "security-1")
        development1 = next(t for t in result["tasks"] if t["id"] == "development-1")
        security2 = next(t for t in result["tasks"] if t["id"] == "security-2")
        self.assertEqual(security1["status"], "rejected")
        self.assertIn("security finding not bound", security1["record"]["defects"][0])
        self.assertEqual(development1["status"], "accepted")
        self.assertEqual(security2["status"], "accepted")

    def test_security_high_finding_commissions_application_correction(self):
        self.provider.security_findings = {"security-1": [{"severity": "high", "title": "Unsafe input handling", "file": "index.html", "defect": "Untrusted stored input is parsed without a size guard."}]}
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "prepared_with_research_blocked")
        security = next(t for t in result["tasks"] if t["id"] == "security-1")
        development = next(t for t in result["tasks"] if t["id"] == "development-1")
        self.assertEqual(security["status"], "rejected")
        self.assertIn("blocking security finding", security["record"]["defects"][0])
        self.assertEqual(development["status"], "rejected")
        self.assertEqual(development["record"]["review_failure"]["task_id"], "security-1")

    def test_real_check_failure_is_logged_and_bounded(self):
        self.provider.fail_checks = True
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["budget"]["task_budget_exhausted"])
        failures = [t for t in result["tasks"] if t["role"] == "testing"]
        self.assertGreater(len(failures), 6)
        self.assertLessEqual(len(result["tasks"]), CAPABILITIES["max_tasks"])
        self.assertTrue(all(t["status"] == "rejected" for t in failures))
        self.assertTrue(all(t["record"]["execution"]["exit_status"] != 0 for t in failures))
        self.assertIn("AssertionError", (self.manager.home / failures[0]["record"]["execution"]["log"]).read_text())

    def test_hash_mismatch_rejects_inspection(self):
        self.provider.tamper_hash = True
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["budget"]["task_budget_exhausted"])
        self.assertTrue(all(t["status"] == "rejected" for t in result["tasks"]
                            if t["role"] in ("testing", "security")))

    def test_plan_cycle_missing_role_and_missing_app_dependency_denied(self):
        bad = plan()
        next(t for t in bad["tasks"] if t["role"] == "development")["depends_on"] = ["testing"]
        with self.assertRaises(ValueError):
            validate_plan(bad)
        bad = plan()
        bad["tasks"].pop()
        with self.assertRaises(ValueError):
            validate_plan(bad)
        bad = plan()
        next(t for t in bad["tasks"] if t["role"] == "testing")["depends_on"] = []
        with self.assertRaises(ValueError):
            validate_plan(bad)

    def test_path_command_and_oversized_files_denied(self):
        for files in ({"../escape.md": "x"}, {"checks.py": "x"}, {"checks.py": "x"}, {"/tmp/x.html": "x"},
                      {"index.html": "x" * 200000}):
            with self.assertRaises(ValueError):
                file_map(files, "development")

    def test_testing_worker_may_return_bounded_javascript_test_artifacts(self):
        files = {"checks.py": "assert True", "browser-journey.cjs": "process.exit(0)",
                 "browser-journey.js": "process.exit(0)", "browser-journey.mjs": "process.exit(0)",
                 "RESULT-TEMPLATE.json": "{}", "TESTING.md": "bounded test artifact"}
        self.assertEqual(file_map(files, "testing"), files)
        for files in ({"run.sh": "#!/bin/sh"}, {"index.html": "<script></script>"},
                      {"../escape.cjs": "process.exit(0)"}):
            with self.assertRaises(ValueError):
                file_map(files, "testing")

    def test_task_state_and_accepted_output_tamper_fail_closed(self):
        self.manager.run_agents()
        task = next(t for t in self.manager.tasks() if t["role"] == "development")
        p = self.manager.home / task["record"]["artifacts"][0]["path"]
        p.write_text("tampered")
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "blocked")
        self.manager.db.execute("UPDATE tasks SET status='pending'")
        self.manager.db.commit()
        with self.assertRaises(ValueError):
            self.manager.verify_agent_state()

    def test_interrupted_inference_never_replayed(self):
        self.manager.save("calls", [{"id": "manager-plan", "status": "running"}])
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(self.provider.calls, [])

    def test_call_bound(self):
        self.manager.save("calls", [{"status": "returned"}] * CAPABILITIES["max_inference_calls"])
        with self.assertRaises(ValueError):
            self.manager.infer("extra", "manager", {}, "{}")
        self.assertEqual(self.provider.calls, [])

    def test_research_never_invents_sources(self):
        result = self.manager.run_agents()
        research = next(t for t in result["tasks"] if t["role"] == "research")
        self.assertEqual(research["record"]["evidence"]["sources"], [])
        self.assertEqual(research["record"]["evidence"]["claims"], [])
        self.assertEqual(research["record"]["research_status"], "policy_blocked")

    def test_provider_config_and_gate_blocks_no_fixture_fallback(self):
        self.manager.test_provider = None
        for failure in (ModelProviderError("provider configuration required; fixtures forbidden"),
                        CertificationGateError("gate test only")):
            # Fresh identity per blocked attempt, as required by recovery policy.
            with patch("provider_manager.configured_provider", side_effect=failure):
                result = self.manager.run_agents()
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(self.provider.calls, [])
            self.assertEqual(result["tasks"], [])
            self.assertFalse(any(c.get("agent_inference") for c in result["calls"]))

    def test_approved_provider_preserves_shorter_timeout_and_caps_longer_timeout(self):
        self.manager.test_provider = None
        default_adapter = OpenAICompatibleShadowModel("https://example.invalid/v1", "test-model", "test-token")

        for identity, role, timeout in (("research-1", "research", 30.0), ("manager-research-2", "manager", 300.0)):
            with self.subTest(identity=identity):
                adapter = OpenAICompatibleShadowModel("https://example.invalid/v1", "test-model", "test-token")
                adapter.timeout = timeout
                original = dict(adapter.__dict__)

                def respond(provider, request, schemas):
                    self.assertIs(provider, adapter)
                    self.assertEqual(provider.timeout, min(timeout, 240.0))
                    self.assertEqual(schemas, ())
                    self.assertEqual(request["opportunity"]["task_id"], identity)
                    self.assertIs(request["json_object_mode"], True)
                    # Synthetic trace only; the adapter's network method is replaced.
                    provider.trace_path.write_text(json.dumps({
                        "status": "PASS", "response_sha256": hashlib.sha256(b"{}").hexdigest()
                    }) + "\n")
                    return {"decision": {"content": "{}"}, "tool_call": None}

                with patch("provider_manager.configured_provider", return_value=adapter) as factory, \
                        patch.object(OpenAICompatibleShadowModel, "__call__", autospec=True,
                                     side_effect=respond) as invoke:
                    self.assertEqual(self.manager.infer(identity, role, {}, "{}"), {})
                factory.assert_called_once()
                self.assertTrue(factory.call_args.kwargs["required"])
                invoke.assert_called_once()
                expected = {**original, "timeout": min(timeout, 240.0),
                            "trace_path": self.manager.home / "inference" / identity / "provider-trace.jsonl"}
                self.assertEqual(adapter.__dict__, expected)
                self.assertEqual(default_adapter.timeout, 30.0)

    def test_gate_block_is_observed_before_provider_execution(self):
        self.manager.test_provider = None
        with patch("provider_manager.configured_provider", side_effect=CertificationGateError("test gate")) as factory:
            result = self.manager.run_agents()
        factory.assert_called_once()
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["calls"][0]["provider_invoked"])
        self.assertEqual(result["calls"][0]["failure_type"], "CertificationGateError")

    def test_plan_evidence_tamper_is_detected(self):
        self.manager.run_agents()
        (self.manager.home / "inference/manager-plan/response.json").write_text("{}")
        with self.assertRaises(ValueError):
            self.manager.verify_agent_state()

    def test_application_failure_commissions_development_correction(self):
        original = self.provider.__call__
        def respond(request, schemas):
            result = original(request, schemas)
            if request["opportunity"]["task_id"] == "testing-1":
                answer = json.loads(result["decision"]["content"])
                answer["files"]["checks.py"] += "raise AssertionError('application defect')\\n"
                result["decision"]["content"] = json.dumps(answer)
            return result
        self.manager.test_provider = respond
        result = self.manager.run_agents()
        self.assertEqual(result["status"], "prepared_with_research_blocked")
        dev = self.manager.effective("development-1")
        self.assertEqual(dev["id"], "development-2")
        test = self.manager.effective("testing-1")
        self.assertEqual(test["record"]["dependency_versions"]["development-1"]["id"], "development-2")

    def test_contained_generated_code_cannot_escape_or_spawn_or_network(self):
        self.manager.plan()
        app = {"index.html": "<title>app</title>"}
        task = {"id": "containment-probe"}
        (self.manager.home / task["id"]).mkdir()
        script = """import socket, subprocess
from pathlib import Path
for action in (lambda: Path('/etc/passwd').read_text(),
               lambda: Path('../escape').write_text('x'),
               lambda: socket.socket(),\n               lambda: subprocess.run(['/usr/bin/true'])):
    try:
        action()
    except (PermissionError, OSError):
        continue
    raise AssertionError('boundary failed')
print('all denied')
"""
        result = self.manager.check_script(task, {"checks.py": script}, app)
        self.assertEqual(result["exit_status"], 0,
                         (self.manager.home / result["log"]).read_text())

if __name__ == "__main__":
    unittest.main()
