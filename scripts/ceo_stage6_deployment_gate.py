"""Offline, fail-closed gate for the Stage6 CEO candidate. No deployment code.

Reconstruct exact recorded installed Python bytes inside the project. Historical
disk identity never attests current installations or loaded process bytes.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "tests/acceptance-evidence/ceo-legacy-units-20261104/final.json"
OUT = ROOT / "tests/acceptance-evidence/ceo-stage6-20261104"
TREES = {
    "ceo": "/usr/local/lib/venture-ceo-level2c/",
    "broker": "/usr/local/lib/venture-control-broker-level2c/",
}
CANDIDATES = {
    "agents/ceo/ceo_research_review.py",
    "agents/ceo/hierarchy_providers.py",
    "agents/ceo/provider_gateway.py",
    "agents/ceo/provider_reservation.py",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def recorded_blob(rel, expected):
    path = ROOT / rel
    if path.is_file() and sha(path.read_bytes()) == expected:
        return path.read_bytes()
    history = subprocess.check_output(
        ["git", "log", "--format=%H", "--", rel], cwd=ROOT, text=True)
    for revision in history.splitlines():
        result = subprocess.run(["git", "show", revision + ":" + rel],
                                cwd=ROOT, capture_output=True)
        if result.returncode == 0 and sha(result.stdout) == expected:
            return result.stdout
    raise ValueError("Unreconstructable recorded Python source: " + rel)


def blockers(broker_reservation, broker_http, broker_entrypoint):
    # These are necessary source capabilities, never sufficient runtime proof.
    reasons = []
    if "CONTROL_LEDGER_V1" not in broker_reservation:
        reasons.append("INSTALLED_BROKER_REJECTS_TRACKED_CEO_RESERVATION")
    tree = ast.parse(broker_http)
    readonly = [node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == "do_GET"]
    if not readonly or not any("exchange_sessions" in ast.unparse(node)
                              and "remote_reservations" in ast.unparse(node)
                              for node in readonly):
        reasons.append("NO_EXISTING_READ_ONLY_CEO_SESSION_AND_CALL_PROOF_API")
    if 'role="ceo"' not in broker_entrypoint and "role='ceo'" not in broker_entrypoint:
        reasons.append("BROKER_ENTRYPOINT_HAS_NO_CEO_EXECUTION_BINDING")
    # No user-supplied booleans can satisfy these independent evidence gaps.
    reasons.extend([
        "CURRENT_INSTALLED_AND_LOADED_BYTES_NOT_ATTESTED",
        "CEO_LOCAL_AUTHORITY_BINDING_NOT_PROVEN",
        "ACTIVE_PROCESS_AND_PENDING_WORK_ISOLATION_NOT_PROVEN",
        "GITHUB_CLAUDE_REVIEW_NOT_VERIFIED",
    ])
    return reasons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconstruct", action="store_true",
                        help="write public recorded Python sources under artifacts")
    args = parser.parse_args()
    assert Path.cwd().resolve() == ROOT
    hashes = json.loads(RECORD.read_text())["hashes"]
    manifest, sources = [], {}
    target = ROOT / "artifacts/ceo-stage6-installed"
    for tree, prefix in TREES.items():
        for installed, expected in sorted(hashes.items()):
            if not installed.startswith(prefix) or not installed.endswith(".py"):
                continue
            rel = installed[len(prefix):]
            if Path(rel).is_absolute() or ".." in Path(rel).parts:
                raise ValueError("Unsafe recorded path")
            raw = recorded_blob(rel, expected)
            sources[tree, rel] = raw.decode()
            candidate = (ROOT / rel).read_bytes() if tree == "ceo" and rel in CANDIDATES else raw
            manifest.append(dict(tree=tree, path=rel, installed_sha256=expected,
                                 candidate_sha256=sha(candidate),
                                 candidate_override=candidate != raw))
            if args.reconstruct:
                for profile, content in (("installed", raw), ("candidate", candidate)):
                    destination = target / profile / tree / rel
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(content)
    reasons = blockers(
        sources["broker", "agents/ceo/provider_reservation.py"],
        sources["broker", "kernel/broker/isolated_mtls.py"],
        sources["broker", "kernel/broker/mtls_server.py"])
    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(classification="EXACT_RECORDED_INSTALLED_SOURCE_RECONSTRUCTION",
                  source_record_sha256=sha(RECORD.read_bytes()),
                  deployment_allowed=False, blockers=reasons,
                  current_installation_verified=False, production_state_accessed=False,
                  files=manifest)
    (OUT / "deployment-gate.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(deployment_allowed=False, blockers=reasons,
                         reconstructed_python_files=len(manifest)), indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
