"""Mocked HTTP evidence only: no credentials, network or genuine inference."""
import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
import urllib.request
import urllib.response
from pathlib import Path
from unittest.mock import patch

from agents.ceo.provider import ModelProviderError, OpenAICompatibleShadowModel
from agents.ceo.venture_exercise import ROOT, cli, fixture
from kernel.p6.registry import LIVE_FIELDS


class Response:
    def __init__(self, value):
        self.data = json.dumps(value).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size=-1):
        return self.data


class CEOProviderEntrypointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.path = Path(self.tmp.name)
        self.gate = self.path / "test-only-gate.json"
        # Test fixture, never a real certification record.
        self.gate_record = dict(
            gate_name="pre-ceo-kernel-certification", status="PASS",
            suite="ADV-001..ADV-049", pass_count=49, universe=49, pending_count=0,
            unauthorized_external_actions=0, role_bound_red_team_identities=True,
            reasoning_model_attached=False,
        )
        self.gate.write_text(json.dumps(self.gate_record))
        self.env = dict(CEO_MODEL_ENDPOINT="https://provider.example/v1",
                        CEO_MODEL_NAME="mock-model", CEO_MODEL_TOKEN="test-only-token",
                        CEO_KERNEL_GATE_FILE=str(self.gate))
        self.database = self.path / "flow.sqlite"
        self.report = self.path / "report.json"
        self.stages = []
        self.attack = None

    def tearDown(self):
        self.tmp.cleanup()

    def transport(self, request, **kwargs):
        self.assertEqual(request.full_url, "https://provider.example/v1/chat/completions")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-only-token")
        self.assertEqual(kwargs["timeout"], 30.0)
        body = json.loads(request.data)
        self.assertEqual(set(body), {"model", "messages"})
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])
        opportunity = json.loads(body["messages"][1]["content"])
        stage = opportunity["stage"]
        self.stages.append(stage)
        value = {"id": "mock-" + stage, "model": "mock-model", "choices": [{
            "message": {"content": json.dumps(fixture(stage, opportunity["context"]))},
            "finish_reason": "stop",
        }]}
        if self.attack:
            self.attack(stage, value)
        return Response(value)

    def invoke(self, *extra, env=None):
        args = ["exercise", "--durable-ceo", "--require-provider",
                "--database", str(self.database), "--report", str(self.report), *extra]
        output = io.StringIO()
        with patch.dict("os.environ", self.env if env is None else env, clear=True), \
             patch("sys.argv", args), contextlib.redirect_stdout(output), \
             patch("agents.ceo.provider.urllib.request.OpenerDirector.open",
                   side_effect=self.transport), \
             patch("agents.ceo.venture_exercise.fixture",
                   side_effect=AssertionError("fixture fallback forbidden")):
            code = cli()
        return code, output.getvalue()

    def test_required_provider_uses_actual_adapter_three_stages_and_replays(self):
        self.assertEqual(self.invoke()[0], 0)
        self.assertEqual(self.stages, ["evaluation", "manager", "review"])
        first = json.loads(self.report.read_text())
        self.assertEqual(first["model_call_count"], 3)
        self.assertFalse(first["ai_inference_independently_verified"])
        self.assertEqual(first["external_action_count"], 0)
        self.assertEqual(first["stored"]["available_to_spend_cents"], 0)
        self.assertEqual(len(first["stored"]["flow"]["worker_results"]), 3)
        for item in [first, *first["evidence"]]:
            for field in LIVE_FIELDS:
                self.assertIs(item[field], False)
        self.assertEqual(self.invoke()[0], 0)
        replay = json.loads(self.report.read_text())
        self.assertEqual(replay["model_call_count"], 0)
        self.assertEqual(first["stored"], replay["stored"])
        self.assertEqual(len(self.stages), 3)
        with contextlib.closing(sqlite3.connect(self.database.with_suffix(".decisions.sqlite"))) as db:
            self.assertEqual(db.execute(
                "SELECT state FROM shadow_decisions").fetchall(), [("completed",)] * 3)

    def test_preflight_checks_gate_but_creates_no_files_or_calls(self):
        code, output = self.invoke("--check-provider")
        self.assertEqual(code, 0)
        self.assertIn("reachability unverified", output)
        self.assertFalse(self.database.exists())
        self.assertFalse(self.report.exists())
        self.assertFalse(self.database.with_suffix(".decisions.sqlite").exists())
        self.assertEqual(self.stages, [])

    def test_absent_and_partial_configuration_fail_before_files_or_transport(self):
        for env in [{}, {"CEO_MODEL_NAME": "mock-model"}]:
            with self.subTest(env=env):
                code, output = self.invoke(env=env)
                self.assertEqual(code, 2)
                self.assertIn("no fixture fallback", output)
                self.assertFalse(self.database.exists())
                self.assertFalse(self.report.exists())
        self.assertEqual(self.stages, [])

    def test_missing_gate_configuration_denied(self):
        env = dict(self.env)
        del env["CEO_KERNEL_GATE_FILE"]
        self.assertEqual(self.invoke(env=env)[0], 2)
        self.assertFalse(self.database.exists())
        self.assertEqual(self.stages, [])

    def test_gate_missing_failed_or_wrong_denominator_blocks_transport(self):
        self.gate.unlink()
        self.assertEqual(self.invoke()[0], 3)
        for field, value in [("status", "FAIL"), ("universe", 50), ("pass_count", 48)]:
            record = dict(self.gate_record, **{field: value})
            self.gate.write_text(json.dumps(record))
            self.assertEqual(self.invoke()[0], 3)
        self.assertEqual(self.stages, [])
        self.assertFalse(self.database.exists())

    def test_required_mode_refuses_non_durable_entry(self):
        with patch("sys.argv", ["exercise", "--require-provider"]), \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
            cli()
        self.assertEqual(exc.exception.code, 2)

    def test_transport_failure_is_sanitized_terminal_and_never_allocates(self):
        def fail(stage, value):
            if stage == "manager":
                raise OSError("sensitive-remote-body test-only-token")
        self.attack = fail
        code, output = self.invoke()
        self.assertEqual(code, 2)
        self.assertNotIn("sensitive-remote-body", output)
        self.assertNotIn("test-only-token", output)
        self.assertFalse(self.report.exists())
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM ledger").fetchone()[0], 0)
        with contextlib.closing(sqlite3.connect(self.database.with_suffix(".decisions.sqlite"))) as db:
            self.assertEqual(sorted(db.execute(
                "SELECT state FROM shadow_decisions").fetchall()),
                [("completed",), ("rejected",)])
        self.attack = None
        self.assertEqual(self.invoke()[0], 4)
        self.assertEqual(self.stages, ["evaluation", "manager"])

    def test_unsolicited_modern_and_legacy_tools_rejected_before_workers(self):
        for field, value in [
            ("tool_calls", [{"function": {"name": "shell", "arguments": "{}"}}]),
            ("function_call", {"name": "shell", "arguments": "{}"}),
        ]:
            def attack(stage, response):
                response["choices"][0]["message"][field] = value
            self.attack = attack
            self.assertEqual(self.invoke()[0], 2)
            self.assertFalse(self.report.exists())
            with contextlib.closing(sqlite3.connect(self.database)) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM ledger").fetchone()[0], 0)
            # A distinct request store avoids replaying the previous terminal denial.
            self.database = self.path / "other.sqlite"
        self.assertEqual(self.stages, ["evaluation", "evaluation"])

    def test_model_authority_and_malformed_json_fail_closed(self):
        for attack_kind in ["authority", "json"]:
            def attack(stage, value):
                message = value["choices"][0]["message"]
                if attack_kind == "authority":
                    parsed = json.loads(message["content"])
                    parsed["capital_authorized"] = True
                    message["content"] = json.dumps(parsed)
                else:
                    message["content"] = '{"duplicate":1,"duplicate":2}'
            self.attack = attack
            self.assertEqual(self.invoke()[0], 4)
            self.assertFalse(self.report.exists())
            with contextlib.closing(sqlite3.connect(self.database.with_suffix(".decisions.sqlite"))) as db:
                self.assertEqual(db.execute(
                    "SELECT state FROM shadow_decisions").fetchall(), [("quarantined",)])
            self.database = self.path / "other.sqlite"

    def test_json_object_mode_is_explicit_and_disallowed_with_tools(self):
        provider = OpenAICompatibleShadowModel(
            "https://provider.example/v1", "mock-model", "test-only-token")
        observed = {}

        def transport(request, timeout):
            observed["body"] = json.loads(request.data)
            observed["timeout"] = timeout
            return Response({"id": "mock-json", "model": "mock-model", "choices": [{
                "message": {"content": "{\"ok\":true}"}, "finish_reason": "stop",
            }]})

        with patch.object(provider._opener, "open", side_effect=transport):
            result = provider({"system": "return JSON", "opportunity": {},
                               "json_object_mode": True}, ())
        self.assertEqual(result["decision"]["content"], "{\"ok\":true}")
        self.assertEqual(observed["body"]["response_format"], {"type": "json_object"})
        self.assertEqual(observed["body"]["model"], "mock-model")
        self.assertEqual(observed["timeout"], 30.0)
        for request, tools in (({"system": "x", "opportunity": {}, "json_object_mode": "yes"}, ()),
                               ({"system": "x", "opportunity": {}, "json_object_mode": True},
                                ("capital-allocation-request.schema.json",))):
            with self.subTest(request=request, tools=tools):
                with self.assertRaises(ModelProviderError):
                    provider(request, tools)

    def test_endpoint_cannot_embed_credentials_or_use_cleartext(self):
        for endpoint in ["http://provider.example/v1", "file:///data",
                         "https://user:password@provider.example/v1",
                         "https://provider.example/v1?token=secret",
                         "https://provider.example/v1#fragment",
                         "https://provider.example:bad/v1"]:
            env = dict(self.env, CEO_MODEL_ENDPOINT=endpoint)
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.invoke(env=env)[0], 2)
        self.assertEqual(self.stages, [])
        self.assertFalse(self.database.exists())

    def test_redirect_handler_blocks_cross_origin_and_same_origin_redirects(self):
        provider = OpenAICompatibleShadowModel(
            "https://provider.example/v1", "mock-model", "test-only-token")
        for target in ["https://other.example/stolen", "https://provider.example/new"]:
            response = urllib.response.addinfourl(
                io.BytesIO(b""), {"location": target}, provider.endpoint, 302)
            response.msg = "redirect"
            with patch("urllib.request.HTTPSHandler.https_open", return_value=response) as send:
                with self.assertRaises(ModelProviderError):
                    provider({"system": "test", "opportunity": {}}, ())
                self.assertEqual(send.call_count, 1)


if __name__ == "__main__":
    unittest.main()
