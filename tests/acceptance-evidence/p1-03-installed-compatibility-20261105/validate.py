"""Reproduce P1-03 using recorded public Python bytes, inside the project only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd().resolve()
assert ROOT == Path("/home/epsilon/venture-control-workspace")
OUT = ROOT / "tests/acceptance-evidence/p1-03-installed-compatibility-20261105"
HIST = ROOT / "tests/acceptance-evidence/ceo-attestation-20261105"
TREE = ROOT / "artifacts/p1-03-installed-compatibility-20261105-v3"
assert not TREE.exists(), "Use a new isolated tree; never reuse stale package bytes"
TMP = TREE / "tmp"
TMP.mkdir(parents=True)
env = dict(os.environ, TMPDIR=str(TMP), PYTHONDONTWRITEBYTECODE="1",
           PYTHONPATH=str(ROOT) + ":" + str(ROOT / "tests"))
sha = lambda raw: hashlib.sha256(raw).hexdigest()
report = json.loads((HIST / "attestation.json").read_text())
overlays = json.loads((HIST / "candidate-overlays.json").read_text())
manifest = {}
for label, data in report["sources"].items():
    assert not data["walk_errors"]
    for entry in data["files"]:
        rel = entry["path"]
        assert not Path(rel).is_absolute() and ".." not in Path(rel).parts
        raw = (ROOT / "artifacts/ceo-attestation-installed/installed" / label / rel).read_bytes()
        assert sha(raw) == entry["result"]["sha256"], (label, rel)
        for profile in ("installed", "candidate"):
            target = TREE / profile / label / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        manifest[label, rel] = dict(profile=label, path=rel,
            attested_installed_sha256=sha(raw), candidate_sha256=sha(raw),
            source_sha256=sha((ROOT / rel).read_bytes()) if (ROOT / rel).is_file() else None,
            origin="RECORDED_INSTALLED_BYTES")
for entry in overlays:
    label, rel = entry["tree"], entry["path"]
    raw = subprocess.check_output(["git", "show", report["head"] + ":" + rel], cwd=ROOT)
    assert sha(raw) == entry["sha256"]
    (TREE / "candidate" / label / rel).write_bytes(raw)
    manifest.setdefault((label, rel), dict(profile=label, path=rel,
        attested_installed_sha256=None, source_sha256=sha((ROOT / rel).read_bytes())))
    manifest[label, rel].update(candidate_sha256=sha(raw), origin="EXPLICIT_STAGE7_OVERLAY")

results = {}
def run(name, profile, label, modules):
    output = OUT / name
    output.mkdir()
    command = [sys.executable, "-B", str(ROOT / "scripts/ceo_strict_installed_dry_run.py"),
        str(TREE / profile), label, str(output), *modules]
    with (output / "tests.log").open("w") as log:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                                stderr=subprocess.STDOUT, timeout=180)
    (output / "exit.txt").write_text(str(result.returncode) + "\n")
    (output / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    results[name] = result.returncode
    return result.returncode

ceo_tests = ["tests.test_ceo_pending_recovery", "tests.test_ceo_candidate_acceptance"]
assert run("before-fixture", "candidate", "ceo", ceo_tests) == 1
before = (OUT / "before-fixture/tests.log").read_text()
assert "Ran 17 tests" in before and "FAILED (errors=2)" in before
assert before.count("AttributeError: module 'kernel' has no attribute 'finance'") == 2
before_imports = json.loads((OUT / "before-fixture/ceo-imports.json").read_text())
assert before_imports["missing_installed_dependencies"] == ["integrations", "integrations"]

# Explicit test dependency packaging, never a finder fallback or live install.
# These existing public source files supply the fixture's deny-operation patch
# targets and the eager kernel.finance initializer's transitive imports.
for label in ("ceo", "broker"):
    for rel in ("integrations/payment_adapter/__init__.py",
                "integrations/payment_adapter/real.py",
                "integrations/payment_adapter/simulated.py"):
        raw = subprocess.check_output(["git", "show", report["head"] + ":" + rel], cwd=ROOT)
        assert raw == (ROOT / rel).read_bytes()
        target = TREE / "candidate" / label / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        manifest[label, rel] = dict(profile=label, path=rel,
            source_sha256=sha(raw), attested_installed_sha256=None,
            candidate_sha256=sha(raw), origin="EXPLICIT_TEST_GUARD_DEPENDENCY")

assert run("candidate-ceo", "candidate", "ceo", ceo_tests) == 0
assert run("installed-broker", "installed", "broker",
           ["tests.test_broker_isolated_mtls"]) == 0
assert run("candidate-broker", "candidate", "broker",
           ["tests.test_broker_isolated_mtls", "tests.test_broker_mtls_entrypoint"]) == 0

assert run("candidate-ceo-route", "candidate", "ceo", ["tests.test_ceo_broker"]) == 0

command = [sys.executable, "-B",
    "tests/acceptance-evidence/ceo-stage5-20261104/verify_synthetic.py",
    "tests.test_ceo_installed_compatibility", "tests.test_ceo_stage6_gate",
    "tests.test_ceo_pending_recovery", "tests.test_ceo_candidate_acceptance"]
with (OUT / "regression.log").open("w") as log:
    result = subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                           stderr=subprocess.STDOUT, timeout=180)
(OUT / "regression.exit").write_text(str(result.returncode) + "\n")
results["regression"] = result.returncode
assert result.returncode == 0

subprocess.run([sys.executable, "-B", str(OUT / "finalize.py")], cwd=ROOT, check=True)
