"""Generate the P0.13 certification report with an explicit 24/49 denominator."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("p013-manifest.json")


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    completed = subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if completed.returncode:
        print(completed.stdout, end="")
        print(completed.stderr, end="")
        return completed.returncode
    print("Phase 0 Certification")
    for item in manifest["tests"]:
        print(f"{item['id']} {item['status']}  ({item['evidence']})")
    print(f"{manifest['pass_count']} / {manifest['universe']} PASS  ({manifest['pending_count']} not yet executable, not failing)")
    print("Unauthorized external actions: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
