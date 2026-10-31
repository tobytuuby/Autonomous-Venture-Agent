#!/usr/bin/env python3
"""Offline integrity and consistency check; never claims live acceptance."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def canonical_sha(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"),
                          allow_nan=False).encode())
def read(name):
    return json.loads((BASE / name).read_text())
def main():
    listed = set()
    for line in (BASE / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert "/" not in name and name not in listed
        listed.add(name)
        path = BASE / name
        assert not path.is_symlink() and path.is_file()
        assert sha(path.read_bytes()) == digest, name
    actual = {p.name for p in BASE.iterdir() if p.is_file()} - {"SHA256SUMS"}
    assert listed == actual, (listed, actual)
    manifest = read("manifest.json")
    observation = read("control-observation.json")
    fixture = read("fixture.json")
    assert manifest["verdict"] == observation["verdict"] == "BLOCKED"
    assert observation["journey_executed"] is False
    for name, expected in manifest["canonical_json_sha256"].items():
        assert canonical_sha(read(name)) == expected, name
    workers = [actor for actor, role in observation["trust"]["actors"].items() if role == "worker"]
    assert workers == ["service-worker"]
    assert observation["worker_policy"]["fields"]["actor_id"] == workers[0]
    assert observation["worker_policy"]["fields"]["maximum_requests"] == 4
    assert observation["service"]["ActiveState"] == "active"
    broker = observation["sources"]["kernel/broker/mtls_server.py"]
    binding = [line for line in broker["excerpts"] if 'actor="service-worker"' in line["text"]]
    assert len(binding) == 2
    for value in observation["sources"].values():
        assert value["sha256"] == value["local_checkout_sha256"]
    assert fixture["status"] == "PLANNED_NOT_CREATED"
    assert fixture["workflow_id"] not in ["level2d-acceptance-" + str(n) for n in range(1, 6)]
    assignments = fixture["assignments"]
    assert len({item["worker_id"] for item in assignments}) == 3
    assert assignments[2]["depends_on"] == ["A", "B"]
    assert all(value == "NOT_RUN" for value in manifest["live_evidence"].values())
    log = (BASE / "local-tests.log").read_text()
    assert "Ran 48 tests in 7.332s" in log and "\nOK\n" in log and log.endswith("EXIT_CODE=0\n")
    assert len([line for line in log.splitlines() if line.endswith(" ... ok")]) == 48
    for name, digest in observation["dirty_tracked_sha256"].items():
        assert sha((ROOT / name).read_bytes()) == digest, "unrelated file changed: " + name
    print("BLOCKER_EVIDENCE_VERIFIED; LIVE_JOURNEY_NOT_RUN; local tests 48/48")
if __name__ == "__main__":
    main()
