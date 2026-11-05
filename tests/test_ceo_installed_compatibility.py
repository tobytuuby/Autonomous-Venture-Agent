"""Missing installed modules must fail even when checkout modules exist."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstalledCompatibilityTests(unittest.TestCase):
    def test_missing_installed_modules_never_fall_back_to_checkout(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as temporary:
            tree = Path(temporary)
            # Package paths intentionally point at the checkout, as in the
            # acceptance harness. The finder must still deny missing children.
            for package in ("agents", "kernel"):
                destination = tree / "ceo" / package
                destination.mkdir(parents=True)
                (destination / "__init__.py").write_text("")
            (tree / "ceo/integrations").mkdir()
            for module in ("agents.ceo.ceo_broker", "kernel.finance.finance",
                           "integrations.payment_adapter"):
                with self.subTest(module=module):
                    code = """
import importlib
import sys
from pathlib import Path
from scripts.ceo_strict_installed_dry_run import Finder
finder = Finder(Path(sys.argv[1]), "ceo")
sys.meta_path.insert(0, finder)
try:
    importlib.import_module(sys.argv[2])
except ImportError as error:
    assert str(error).startswith("Recorded installed dependency absent:"), str(error)
    assert finder.missing, "missing import was not recorded"
    print(str(error))
else:
    raise AssertionError("silent repository fallback")
"""
                    result = subprocess.run([sys.executable, "-B", "-c", code,
                        str(tree), module], cwd=ROOT, capture_output=True, text=True,
                        timeout=10)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("Recorded installed dependency absent:", result.stdout)
