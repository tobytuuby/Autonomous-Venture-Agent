"""Synthetic import profile from recorded installed hashes; no installed reads/writes.

Load each recorded module from a matching reachable Git blob, in memory. Only
four reviewed CEO dependencies use the repository candidate. This is historical
dependency emulation, not fresh attestation of a running process or installation.
"""
import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path.cwd().resolve()
assert ROOT == Path("/home/epsilon/venture-control-workspace")
OUT = ROOT / "tests/acceptance-evidence/ceo-stage5-20261104"
RECORD = ROOT / "tests/acceptance-evidence/ceo-legacy-units-20261104/final.json"
PREFIX = "/usr/local/lib/venture-ceo-level2c/"
CANDIDATE = {
    "agents.ceo.ceo_research_review", "agents.ceo.hierarchy_providers",
    "agents.ceo.provider_gateway", "agents.ceo.provider_reservation",
}
observed = json.loads(RECORD.read_text())["hashes"]
paths = {}
for path, sha in observed.items():
    if path.startswith(PREFIX) and path.endswith(".py"):
        rel = path[len(PREFIX):]
        name = rel[:-3].replace("/", ".")
        package = name.endswith(".__init__")
        if package:
            name = name[:-9]
        paths[name] = (rel, sha, package)
# The broker wrapper is a broker-owned component, absent from the CEO runtime
# import path. Use its own recorded hash rather than the obsolete CEO-tree copy.
for path, expected in observed.items():
    prefix = "/usr/local/lib/venture-control-broker-level2c/"
    if path.startswith(prefix + "kernel/broker/") and path.endswith(".py"):
        rel = path[len(prefix):]
        name = rel[:-3].replace("/", ".")
        package = name.endswith(".__init__")
        if package:
            name = name[:-9]
        paths[name] = (rel, expected, package)
loaded, missing = [], set()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class RecordedLoader(importlib.abc.Loader):
    def __init__(self, name, rel, expected, package):
        self.name, self.rel, self.expected, self.package = name, rel, expected, package

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        path = ROOT / self.rel
        current = path.read_bytes() if path.is_file() else None
        revision = None
        if self.name in CANDIDATE:
            raw, source = current, "REPOSITORY_CEO_CANDIDATE"
        elif current is not None and sha(current) == self.expected:
            raw, source = current, "RECORDED_INSTALLED_HASH"
        else:
            raw = None
            history = subprocess.check_output(
                ["git", "log", "--format=%H", "--", self.rel], cwd=ROOT, text=True)
            for rev in history.splitlines():
                blob = subprocess.run(["git", "show", rev + ":" + self.rel],
                    cwd=ROOT, capture_output=True)
                if blob.returncode == 0 and sha(blob.stdout) == self.expected:
                    raw, revision = blob.stdout, rev
                    break
            if raw is None:
                raise ImportError("No reachable source matching recorded hash: " + self.name)
            source = "RECORDED_INSTALLED_HASH"
        if raw is None:
            raise ImportError("Missing bounded candidate source: " + self.name)
        loaded.append(dict(module=self.name, path=self.rel, sha256=sha(raw),
            recorded_sha256=self.expected, revision=revision, source=source,
            recorded_tree="BROKER" if self.name.startswith("kernel.broker") else "CEO"))
        # Preserve the existing ROOT derivation. No code is copied to an install tree.
        module.__file__ = str(path)
        if self.package:
            module.__path__ = [str(path.parent)]
        exec(compile(raw, str(path), "exec"), module.__dict__)


class RecordedFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in paths:
            rel, expected, package = paths[fullname]
            return importlib.util.spec_from_loader(fullname,
                RecordedLoader(fullname, rel, expected, package), is_package=package)
        if fullname.startswith(("agents.", "kernel.", "integrations.")):
            # Test harness-only modules are separately disclosed. A missing
            # installed dependency must not silently become installed evidence.
            missing.add(fullname)
        return None


sys.meta_path.insert(0, RecordedFinder())
names = sys.argv[1:] or ["tests.test_ceo_candidate_acceptance", "tests.test_ceo_pending_recovery"]
try:
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    success = result.wasSuccessful()
finally:
    (OUT / "candidate-imports.json").write_text(json.dumps(dict(
        classification="RECORDED_INSTALLED_DEPENDENCY_EMULATION",
        source_record_sha256=sha(RECORD.read_bytes()), source_record=str(RECORD.relative_to(ROOT)),
        candidate_modules=sorted(CANDIDATE), loaded=loaded,
        repository_fallback_modules=sorted(missing),
        production_loaded_bytes_verified=False, installed_broker_profile_tested=False),
        indent=2) + "\n")
sys.exit(0 if success else 1)
