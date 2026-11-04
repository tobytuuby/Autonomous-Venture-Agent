"""Load only exact reconstructed source bytes; missing installed modules fail.

The test harness is repository code. Installed modules retain repository-relative
__file__ solely for existing root containment checks on synthetic fixture paths.
There is no repository fallback for production package modules.
"""
import hashlib
import importlib.abc
import importlib.util
import ipaddress
import json
from pathlib import Path
import socket
import sys
import unittest

ROOT = Path.cwd().resolve()
assert ROOT == Path("/home/epsilon/venture-control-workspace")
OUT = ROOT / "tests/acceptance-evidence/ceo-stage6-20261104"
TREE = ROOT / "artifacts/ceo-stage6-installed/candidate"
profile = sys.argv[1]
assert profile in ("ceo", "broker")
loaded, missing = [], []
original_connect = socket.socket.connect


def connect(sock, address):
    if sock.family in (socket.AF_INET, socket.AF_INET6):
        try:
            allowed = ipaddress.ip_address(address[0]).is_loopback
        except ValueError:
            allowed = address[0] == "localhost"
        if not allowed:
            raise AssertionError("External network forbidden")
    return original_connect(sock, address)


socket.socket.connect = connect


class Loader(importlib.abc.Loader):
    def __init__(self, path, rel, package, tree):
        self.path, self.rel, self.package, self.tree = path, rel, package, tree

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        raw = self.path.read_bytes()
        loaded.append(dict(module=module.__name__, tree=self.tree,
                           sha256=hashlib.sha256(raw).hexdigest()))
        module.__file__ = str(ROOT / self.rel)
        if self.package:
            module.__path__ = [str((ROOT / self.rel).parent)]
        exec(compile(raw, module.__file__, "exec"), module.__dict__)


class Finder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith(("agents", "kernel", "integrations")):
            return None
        tree = "broker" if fullname.startswith("kernel.broker") else profile
        rel = fullname.replace(".", "/")
        for suffix, package in ((".py", False), ("/__init__.py", True)):
            source = TREE / tree / (rel + suffix)
            if source.is_file():
                return importlib.util.spec_from_loader(fullname,
                    Loader(source, rel + suffix, package, tree), is_package=package)
        directory = TREE / tree / rel
        if directory.is_dir():
            spec = importlib.util.spec_from_loader(fullname, loader=None, is_package=True)
            spec.submodule_search_locations = [str(directory)]
            return spec
        missing.append(fullname)
        raise ImportError("Recorded installed dependency absent: " + fullname)


sys.meta_path.insert(0, Finder())
try:
    suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[2:])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    success = result.wasSuccessful()
finally:
    (OUT / (profile + "-imports.json")).write_text(json.dumps(dict(
        profile=profile, classification="STRICT_RECORDED_INSTALLED_TREE_DRY_RUN",
        current_installation_verified=False, loaded=loaded,
        missing_installed_dependencies=missing, repository_production_fallback=False),
        indent=2) + "\n")
sys.exit(0 if success else 1)
