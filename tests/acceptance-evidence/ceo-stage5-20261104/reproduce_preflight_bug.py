"""Run the split-ledger regression against the frozen pre-fix provider in memory."""
import importlib
import io
from pathlib import Path
import subprocess
import sys
import unittest

assert Path.cwd() == Path("/home/epsilon/venture-control-workspace")
BASELINE = "cbe02523864a8d99463255634d757d9c705eb7ef"
module = importlib.import_module("agents.ceo.hierarchy_providers")
source = subprocess.check_output(
    ["git", "show", BASELINE + ":agents/ceo/hierarchy_providers.py"])
exec(compile(source, module.__file__, "exec"), module.__dict__)
suite = unittest.defaultTestLoader.loadTestsFromName(
    "tests.test_ceo_pending_recovery.CEOPendingRecoveryTests."
    "test_split_local_and_broker_authority_blocks_before_remote_charge")
output = io.StringIO()
result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
print(output.getvalue())
expected = (len(result.failures) == 1 and not result.errors
    and "CEO_RESERVATION_PROOF_REQUIRED" in result.failures[0][1]
    and "CEO_LOCAL_LEDGER_BINDING_REQUIRED" in result.failures[0][1])
print("BASELINE_PREFLIGHT_BUG_REPRODUCED=" + str(expected))
sys.exit(0 if expected else 1)
