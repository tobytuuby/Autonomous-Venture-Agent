"""Fixed local programs, never model-backed agents. No arbitrary commands."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED

sys.path.insert(0, str(Path(__file__).resolve().parent))
from containment import contain

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def execute(role, source, out):
    files = sorted(p for p in source.rglob("*") if p.is_file())
    if role == "research":
        return {"inventory": [{"path": str(p.relative_to(source)), "bytes": p.stat().st_size,
                               "sha256": sha(p)} for p in files],
                "scope": "local supplied documents only; no market or buyer verification"}
    if role == "development":
        product = source / "product"
        with ZipFile(out / "review-kit.zip", "w", ZIP_DEFLATED) as z:
            for name in ("restock.html", "START-HERE.md"):
                z.write(product / name, name)
        return {"operation": "package existing product for offline review",
                "implementation_authorship": "existing product; no AI code generation"}
    if role == "testing":
        # Existing assertions run against the packaged product, not a hand-written result.
        with ZipFile(source / "review-kit.zip") as z:
            target = out / "ventures/venture-001/product"
            target.mkdir(parents=True)
            (target / "restock.html").write_bytes(z.read("restock.html"))
        command = ["/usr/bin/node", "--openssl-config=/dev/null", str(source / "validation/test-restock.js")]
        result = subprocess.run(command, cwd=out, capture_output=True, text=True, timeout=10)
        (out / "assertions.log").write_text(result.stdout + result.stderr)
        return {"command": command, "exit_status": result.returncode,
                "scope": "actual JavaScript worksheet assertions; no browser UI coverage"}
    if role == "security":
        with ZipFile(source / "review-kit.zip") as z:
            html = z.read("restock.html").decode()
        checks = {"remote_script": r'<script[^>]+src\s*=',
                  "network_api": r'\b(fetch|XMLHttpRequest|WebSocket)\s*\(',
                  "dynamic_eval": r'\beval\s*\(',
                  "html_sink": r'\.innerHTML\s*='}
        findings = [name for name, pattern in checks.items() if re.search(pattern, html, re.I)]
        return {"findings": findings, "scope": "bounded static scan, not security certification"}
    if role == "commercial":
        offer = (source / "OFFER.md").read_text()
        return {"price_mentions": sorted(set(re.findall(r'\$\d+(?:\.\d+)?', offer))),
                "source_sha256": sha(source / "OFFER.md"),
                "demand_verified": False, "sales": 0,
                "limitations": "document extraction only; no outreach, market research or transactions"}
    raise ValueError("unavailable worker role")

def main():
    role, source, output = sys.argv[1:]
    source, output = Path(source).resolve(), Path(output).resolve()
    contain(source, output)
    result = execute(role, source, output)
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"role": role, "backend": "fixed_local_program", "result": result}))
    if result.get("exit_status", 0) or result.get("findings"):
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
