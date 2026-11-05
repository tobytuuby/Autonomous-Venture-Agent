"""Offline CLI no-go verification; no live state, inventory, or provider calls."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import ceo_stage6_deployment_gate as gate


class ProductionNoGoTests(unittest.TestCase):
    def test_missing_local_inputs_keep_both_readonly_modes_closed(self):
        with tempfile.TemporaryDirectory(dir=gate.ROOT / "artifacts") as directory:
            root = Path(directory)
            missing = root / "absent"
            for flags, decision in (
                (["--preflight-resume", "--deployment-lock", str(missing)], "DENY"),
                (["--assess-boundary", "--public-trust", str(missing)], "HOLD"),
            ):
                with self.subTest(flags=flags[0]):
                    output = io.StringIO()
                    with patch("sys.argv", ["ceo_stage6_deployment_gate.py", *flags]), \
                            patch.object(gate.subprocess, "run",
                                         side_effect=AssertionError("external command forbidden")), \
                            patch.object(gate.subprocess, "check_output",
                                         side_effect=AssertionError("external command forbidden")), \
                            contextlib.redirect_stdout(output):
                        self.assertEqual(gate.main(), 2)
                    result = json.loads(output.getvalue())
                    self.assertEqual(result["decision"], decision)
                    self.assertIs(result["deployment_allowed"], False)
                    self.assertIs(result["resume_verified"], False)
                    self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
