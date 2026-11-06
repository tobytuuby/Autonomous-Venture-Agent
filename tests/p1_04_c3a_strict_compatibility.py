"""Bounded strict C3A recorded-package checks; project-local fixtures only.

Run from the project root with an unused project-relative output directory.
No live installed path is opened. Existing P1-03 recorded bytes are hash checked;
explicit overlays are declared by the adjacent source-profile manifest.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    assert Path.cwd().resolve() == ROOT
    output = (ROOT / sys.argv[1]).resolve()
    assert output.is_relative_to(ROOT) and not output.exists()
    output.mkdir(parents=True, mode=0o700)
    manifest = json.loads((ROOT / "tests/fixtures/p1_04_c3a_source_profiles.json").read_text())
    rows = json.loads((ROOT / manifest["recorded_matrix"]).read_text())
    old = ROOT / manifest["recorded_root"]
    tree = output / "candidate"
    evidence = []
    sha = lambda raw: hashlib.sha256(raw).hexdigest()
    for row in rows:
        label, rel = row["profile"], row["path"]
        expected = row.get("candidate_sha256")
        if not expected:
            continue
        source = old / "candidate" / label / rel
        if not source.is_file():
            assert row["module"] is None
            continue
        raw = source.read_bytes()
        assert sha(raw) == expected, str(source)
        target = tree / label / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        evidence.append(dict(profile=label, path=rel, sha256=sha(raw), origin="HASH_VERIFIED_P1_03_RECORDED"))
    for label in manifest["profiles"]:
        for rel in manifest["source_overlays"] + manifest["committed_baseline_overlays"]:
            if rel in manifest["committed_baseline_overlays"]:
                raw = subprocess.check_output(["git", "show", manifest["baseline"] + ":" + rel], cwd=ROOT)
                origin = "EXPLICIT_COMMITTED_BASELINE_OVERLAY"
            else:
                raw = (ROOT / rel).read_bytes()
                origin = "EXPLICIT_C3A_SOURCE_OVERLAY"
            target = tree / label / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            evidence.append(dict(profile=label, path=rel, sha256=sha(raw), origin=origin))
    (output / "tree-manifest.json").write_text(json.dumps(evidence, indent=2) + "\n")
    results = {}
    for profile, modules in manifest["profiles"].items():
        logs = output / profile
        logs.mkdir()
        tmp = logs / "tmp"
        tmp.mkdir()
        env = dict(os.environ, TMPDIR=str(tmp), PYTHONDONTWRITEBYTECODE="1",
                   PYTHONPATH=str(ROOT) + ":" + str(ROOT / "tests"),
                   C3A_STRICT_TREE=str(tree), C3A_STRICT_PROFILE=profile)
        command = [sys.executable, "-B", str(ROOT / "scripts/ceo_strict_installed_dry_run.py"),
                   str(tree), profile, str(logs), *modules]
        (logs / "command.json").write_text(json.dumps(command, indent=2) + "\n")
        with (logs / "tests.log").open("w") as stream:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=120)
        (logs / "exit.txt").write_text(str(result.returncode) + "\n")
        imports = json.loads((logs / (profile + "-imports.json")).read_text())
        assert not imports["repository_production_fallback"]
        assert set(imports["missing_installed_dependencies"]) <= {"integrations.payment_adapter.RealPaymentAdapter"}, imports
        # Every explicit role/dependency overlay must actually be imported from
        # the candidate, with the exact bytes recorded above.
        expected = {row["path"]: row["sha256"] for row in evidence
                    if row["profile"] == profile}
        loaded = {row["path"]: row["sha256"] for row in imports["loaded"]}
        for rel in manifest["source_overlays"] + manifest["committed_baseline_overlays"]:
            assert loaded.get(rel) == expected[rel], (profile, rel, "overlay not loaded")
        assert all(expected[row["path"]] == row["sha256"] for row in imports["loaded"])
        results[profile] = result.returncode
        print(profile, result.returncode, flush=True)
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    return 0 if all(value == 0 for value in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
