"""Verify completed isolated executions and emit exact byte provenance."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path.cwd().resolve()
assert ROOT == Path("/home/epsilon/venture-control-workspace")
OUT = ROOT / "tests/acceptance-evidence/p1-03-installed-compatibility-20261105"
HIST = ROOT / "tests/acceptance-evidence/ceo-attestation-20261105"
TREE = ROOT / "artifacts/p1-03-installed-compatibility-20261105-v3"
sha = lambda raw: hashlib.sha256(raw).hexdigest()
report = json.loads((HIST / "attestation.json").read_text())
manifest = {}
for label, data in report["sources"].items():
    for entry in data["files"]:
        rel = entry["path"]
        installed = sha((TREE / "installed" / label / rel).read_bytes())
        assert installed == entry["result"]["sha256"]
        manifest[label, rel] = dict(profile=label, path=rel,
            attested_installed_sha256=installed, candidate_sha256=installed,
            origin="RECORDED_INSTALLED_BYTES")
for entry in json.loads((HIST / "candidate-overlays.json").read_text()):
    label, rel = entry["tree"], entry["path"]
    manifest.setdefault((label, rel), dict(profile=label, path=rel,
                                         attested_installed_sha256=None))
    manifest[label, rel].update(candidate_sha256=entry["sha256"],
                               origin="EXPLICIT_STAGE7_OVERLAY")
for label in ("ceo", "broker"):
    for filename in ("__init__.py", "real.py", "simulated.py"):
        rel = "integrations/payment_adapter/" + filename
        raw = subprocess.check_output(["git", "show", report["head"] + ":" + rel])
        manifest[label, rel] = dict(profile=label, path=rel,
            attested_installed_sha256=None, candidate_sha256=sha(raw),
            origin="EXPLICIT_TEST_GUARD_DEPENDENCY")
for (label, rel), row in manifest.items():
    assert sha((TREE / "candidate" / label / rel).read_bytes()) == row["candidate_sha256"]
    source = ROOT / rel
    row["source_sha256"] = sha(source.read_bytes()) if source.is_file() else None
    row["module"] = rel.removesuffix(".py").replace("/", ".").removesuffix(".__init__")
    row["observed_required_by"] = []

results, probes = {"before-fixture": 1}, {}
for name in ("candidate-ceo", "candidate-ceo-route", "candidate-broker", "installed-broker"):
    label = "ceo" if name.startswith("candidate-ceo") else "broker"
    assert (OUT / name / "exit.txt").read_text().strip() == "0"
    results[name] = 0
    imports = json.loads((OUT / name / (label + "-imports.json")).read_text())
    # pkgutil.resolve_name first probes this class attribute as a submodule,
    # catches ImportError, then resolves the existing exported class. It is not
    # an absent package dependency. Retain every denied probe in raw evidence.
    assert all(value == "integrations.payment_adapter.RealPaymentAdapter"
               for value in imports["missing_installed_dependencies"])
    probes[name] = imports["missing_installed_dependencies"]
    for entry in imports["loaded"]:
        row = manifest[label, entry["path"]]
        expected = row["attested_installed_sha256"] if name == "installed-broker" else row["candidate_sha256"]
        assert entry["sha256"] == expected
        row["observed_required_by"].append(name)
assert (OUT / "regression.exit").read_text().strip() == "0"
results["regression"] = 0
for row in manifest.values():
    row["observed_required_by"] = sorted(set(row["observed_required_by"]))
(OUT / "source-installed-module-matrix.json").write_text(
    json.dumps(list(manifest.values()), indent=2) + "\n")
historical = ["scripts/ceo_readonly_attestation.py"] + [
    "tests/acceptance-evidence/ceo-attestation-20261105/" + name for name in (
        "attestation.json", "strict_fresh_dry_run.py", "candidate-ceo.log",
        "ceo-imports.json", "candidate-overlays.json")] + [
    "tests/acceptance-evidence/ceo-stage6-20261104/deployment-gate.json",
    "tests/acceptance-evidence/ceo-stage7-review-20261104/SHA256SUMS"]
(OUT / "historical-inputs.json").write_text(json.dumps({
    rel: sha((ROOT / rel).read_bytes()) for rel in historical}, indent=2) + "\n")
(OUT / "results.json").write_text(json.dumps(dict(
    head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    attestation_head=report["head"], test_exits=results,
    classification="OFFLINE_HASH_VERIFIED_RECORDED_BYTES_WITH_EXPLICIT_CANDIDATE_OVERLAYS",
    expected_attribute_resolution_probes=probes,
    unhandled_missing_package_dependencies=[], live_installation_verified=False,
    loaded_production_bytes_verified=False, deployment_allowed=False,
    production_ledger_accessed=False, production_provider_calls=0,
    adv_denominator=49), indent=2) + "\n")
print(json.dumps(results, indent=2))
