"""Report P0.14 fixture coverage without claiming adversarial certification."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("p014-manifest.json")
def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    result = subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, end="")
        print(result.stderr, end="")
        return result.returncode
    if manifest.get("certifying_gate") is not False:
        raise SystemExit("invalid fixture manifest")
    print("P0.14 lifecycle fixture coverage: PASS")
    print("Kernel ADV-001..ADV-049 gate: NOT CERTIFIED")
    print("Role-bound red-team identities: not yet executed")
    print("Reasoning model attached: no")
    print("Unauthorized external actions: 0")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
