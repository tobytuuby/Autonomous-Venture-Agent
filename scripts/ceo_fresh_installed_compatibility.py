"""P1-03: snapshot public installed Python into project fixtures; never deploy.

Only installed agents/kernel/integrations .py files and broker ActiveState are
read. No installed imports, configuration, key, ledger or venture-state access.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'infrastructure/ceo-installed-compatibility.json'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def snapshot(root, packages):
    files = {}
    for package in packages:
        base = root / package
        if not base.exists():
            continue
        assert base.is_dir() and not base.is_symlink(), base
        def failed(error):
            raise error
        for directory, dirs, names in os.walk(base, followlinks=False, onerror=failed):
            dirs[:] = sorted(name for name in dirs if name != '__pycache__')
            for name in dirs:
                assert not (Path(directory) / name).is_symlink()
            for name in sorted(names):
                if not name.endswith('.py'):
                    continue
                path = Path(directory) / name
                assert not path.is_symlink(), path
                files[str(path.relative_to(root))] = path.read_bytes()
    assert files, root
    return files


def main():
    assert Path.cwd().resolve() == ROOT
    output = (ROOT / sys.argv[1]).resolve()
    assert output.is_relative_to(ROOT) and not output.exists()
    output.mkdir(parents=True)
    spec = json.loads(MANIFEST.read_text())
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    tree = ROOT / 'artifacts' / output.name
    assert not tree.exists(), 'Fresh tree required'
    tree.mkdir(parents=True)
    tmp = tree / 'tmp'
    tmp.mkdir()
    env = dict(os.environ, TMPDIR=str(tmp), PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=str(ROOT) + ':' + str(ROOT / 'tests'))
    active = subprocess.check_output(['systemctl', 'show',
        'venture-control-broker-mtls.service', '--property=ActiveState', '--value'],
        text=True).strip()
    assert active == 'active', active
    rows, installed = {}, {}
    for label, source in spec['installed_trees'].items():
        installed[label] = snapshot(Path(source), spec['protected_packages'])
        for rel, raw in installed[label].items():
            for profile in ('installed', 'candidate'):
                target = tree / profile / label / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            rows[label, rel] = dict(profile=label, path=rel,
                installed_sha256=digest(raw), candidate_sha256=digest(raw),
                origin='FRESH_INSTALLED_DISK', observed_by=[])

    def overlay(paths, origin):
        for label in installed:
            for rel in paths:
                assert not Path(rel).is_absolute() and '..' not in Path(rel).parts
                raw = subprocess.check_output(['git', 'show', head + ':' + rel])
                assert raw == (ROOT / rel).read_bytes(), rel
                target = tree / 'candidate' / label / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                row = rows.setdefault((label, rel), dict(profile=label, path=rel,
                    installed_sha256=None, observed_by=[]))
                row.update(candidate_sha256=digest(raw), origin=origin)

    overlay(spec['candidate_source_overlays'], 'EXPLICIT_EXISTING_SOURCE_OVERLAY')
    results = {}
    def run(name, config):
        destination = output / name
        destination.mkdir()
        command = [sys.executable, '-B', str(ROOT / 'scripts/ceo_strict_installed_dry_run.py'),
            str(tree / config['tree']), config['package'], str(destination), *config['tests']]
        (destination / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
        with (destination / 'tests.log').open('w') as log:
            result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=180)
        (destination / 'exit.txt').write_text(str(result.returncode) + '\n')
        results[name] = result.returncode
        return destination

    before = run('before-fixture', spec['profiles']['candidate-ceo'])
    log = (before / 'tests.log').read_text()
    imports = json.loads((before / 'ceo-imports.json').read_text())
    assert results['before-fixture'] == 1 and 'Ran 17 tests' in log
    assert 'FAILED (errors=2)' in log
    assert log.count("AttributeError: module 'kernel' has no attribute 'finance'") == 2
    assert imports['missing_installed_dependencies'] == ['integrations', 'integrations']
    overlay(spec['fixture_only_dependencies'], 'EXPLICIT_TEST_GUARD_DEPENDENCY')
    for name, config in spec['profiles'].items():
        destination = run(name, config)
        assert results[name] == 0, name
        imports = json.loads((destination / (config['package'] + '-imports.json')).read_text())
        assert imports['repository_production_fallback'] is False
        assert set(imports['missing_installed_dependencies']) <= {
            'integrations.payment_adapter.RealPaymentAdapter'}
        for entry in imports['loaded']:
            row = rows[config['package'], entry['path']]
            expected = row['installed_sha256' if config['tree'] == 'installed' else 'candidate_sha256']
            assert entry['sha256'] == expected, entry
            row['observed_by'].append(name)
    # Detect disk drift during the run; do not represent disk as loaded bytecode.
    for label, source in spec['installed_trees'].items():
        assert snapshot(Path(source), spec['protected_packages']) == installed[label], label
    for (_, rel), row in rows.items():
        source = ROOT / rel
        row['source_sha256'] = digest(source.read_bytes()) if source.is_file() else None
        row['observed_by'] = sorted(set(row['observed_by']))
    (output / 'source-installed-matrix.json').write_text(json.dumps(list(rows.values()), indent=2)+'\n')
    (output / 'results.json').write_text(json.dumps(dict(
        head=head, timestamp_utc=datetime.now(timezone.utc).isoformat(),
        manifest_sha256=digest(MANIFEST.read_bytes()), broker_active_state=active,
        classification='FRESH_DISK_SNAPSHOT_SYNTHETIC_EXECUTION_WITH_EXPLICIT_OVERLAYS',
        installed_disk_unchanged_during_run=True, test_exits=results,
        loaded_production_bytes_verified=False, deployment_allowed=False,
        production_provider_calls=0, production_ledger_accessed=False,
        adv_denominator=49), indent=2)+'\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
