"""Strict isolated installed-source tests; never deploys or falls back to checkout.

Based on the preserved 20261105 harness. Repository __file__ values support
existing synthetic root checks only; every protected import is resolved here.
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

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {"agents", "kernel", "integrations"}


class Loader(importlib.abc.Loader):
    def __init__(self, path, rel, package, finder):
        self.path, self.rel, self.package, self.finder = path, rel, package, finder

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        raw = self.path.read_bytes()
        self.finder.loaded.append(dict(module=module.__name__, tree=self.finder.profile,
            path=self.rel, sha256=hashlib.sha256(raw).hexdigest()))
        module.__file__ = str(ROOT / self.rel)
        if self.package:
            module.__path__ = [str((ROOT / self.rel).parent)]
        exec(compile(raw, module.__file__, "exec"), module.__dict__)


class Finder(importlib.abc.MetaPathFinder):
    def __init__(self, tree, profile):
        self.tree, self.profile = Path(tree), profile
        self.loaded, self.missing = [], []

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] not in PACKAGES:
            return None
        rel = fullname.replace(".", "/")
        for suffix, package in ((".py", False), ("/__init__.py", True)):
            source = self.tree / self.profile / (rel + suffix)
            if source.is_file():
                return importlib.util.spec_from_loader(fullname,
                    Loader(source, rel + suffix, package, self), is_package=package)
        directory = self.tree / self.profile / rel
        if directory.is_dir():
            spec = importlib.util.spec_from_loader(fullname, loader=None, is_package=True)
            spec.submodule_search_locations = [str(directory)]
            return spec
        self.missing.append(fullname)
        raise ImportError("Recorded installed dependency absent: " + fullname)


def main():
    assert Path.cwd().resolve() == ROOT
    tree, profile, output, *names = sys.argv[1:]
    assert profile in ("ceo", "broker")
    tree, output = Path(tree).resolve(), Path(output).resolve()
    assert tree.is_relative_to(ROOT) and output.is_relative_to(ROOT)
    output.mkdir(parents=True, exist_ok=True)
    # Fresh process required: a preloaded checkout package could bypass the finder.
    assert not any(name.split(".", 1)[0] in PACKAGES for name in sys.modules)
    finder = Finder(tree, profile)
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
    sys.meta_path.insert(0, finder)
    try:
        suite = unittest.defaultTestLoader.loadTestsFromNames(names)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    finally:
        (output / (profile + "-imports.json")).write_text(json.dumps(dict(
            profile=profile, classification="STRICT_RECORDED_INSTALLED_TREE_DRY_RUN",
            current_installation_verified=False, loaded=finder.loaded,
            missing_installed_dependencies=finder.missing,
            repository_production_fallback=False), indent=2) + "\n")


if __name__ == "__main__":
    sys.exit(main())
