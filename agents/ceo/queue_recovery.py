"""Operator-only terminal abandonment. Never edit historical journals or retry."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import sqlite3

from agents.ceo.escalation_inbox import bounded, exact, identifier, inside_root

RECORD = 'queue.resolution.json'
HISTORY = ('queue.started.json', 'queue.sqlite', 'queue.decisions.sqlite',
           'queue.decisions.jsonl')


def regular(path):
    inside_root(path)
    if not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError('regular unaliased file required')
    return path


def snapshot(state):
    """Read immutable SQLite only after rejecting active recovery sidecars."""
    for name in ('queue.sqlite', 'queue.decisions.sqlite'):
        for suffix in ('-journal', '-wal', '-shm'):
            path = state / (name + suffix)
            if path.exists() or path.is_symlink():
                raise ValueError('operator must reconcile SQLite sidecars first')
    hashes = {name: hashlib.sha256(regular(state / name).read_bytes()).hexdigest()
              for name in HISTORY}
    with sqlite3.connect((state / 'queue.sqlite').as_uri() +
                         '?mode=ro&immutable=1', uri=True) as db:
        cycles = [list(row) for row in db.execute(
            "SELECT id,status,calls FROM cycles WHERE status != 'COMPLETED' ORDER BY id")]
    if not cycles or any(status != 'STARTED' or type(calls) is not int or calls < 0
                         for _, status, calls in cycles):
        raise ValueError('blocked STARTED cycles required')
    return dict(history_sha256=hashes, blocked_cycles=cycles)


def resolution(state):
    path = state / RECORD
    if not path.exists() and not path.is_symlink():
        return None
    raw = regular(path).read_bytes()
    if len(raw) > 16000:
        raise ValueError('resolution bound')
    value = json.loads(raw)
    exact(value, ('version', 'outcome', 'operator', 'reference', 'paid_work',
                  'recorded_at', 'history_sha256', 'blocked_cycles'))
    if value['version'] != 1 or value['outcome'] != 'ABANDONED_NO_RETRY':
        raise ValueError('terminal abandonment required')
    identifier(value['operator'])
    bounded(value['reference'], 300)
    bounded(value['recorded_at'], 100)
    if value['paid_work'] not in ('UNKNOWN', 'RECONCILED'):
        raise ValueError('reconciliation classification required')
    current = snapshot(state)
    if any(value[key] != current[key] for key in current):
        raise ValueError('historical binding changed')
    return value


def abandon(state_dir, *, operator, reference, paid_work):
    """Explicit administrative disposition, not a CEO decision or billing proof.

    UNKNOWN conservatively retains possible paid work. RECONCILED means the
    named operator attests reconciliation at reference; neither permits retry.
    """
    from agents.ceo.scheduled_exercise import now, write_json
    state = inside_root(state_dir)
    identifier(operator)
    bounded(reference, 300)
    if paid_work not in ('UNKNOWN', 'RECONCILED'):
        raise ValueError('reconciliation classification required')
    lock_path = state / 'runner.lock'
    if lock_path.exists():
        regular(lock_path)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'r+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        prior = resolution(state)
        if prior is not None:
            if (prior['operator'], prior['reference'], prior['paid_work']) != (
                    operator, reference, paid_work):
                raise ValueError('resolution is immutable')
            return prior
        value = dict(version=1, outcome='ABANDONED_NO_RETRY', operator=operator,
                     reference=reference, paid_work=paid_work, recorded_at=now(),
                     **snapshot(state))
        write_json(state / RECORD, value, exclusive=True)
        return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', required=True)
    parser.add_argument('--operator', required=True)
    parser.add_argument('--reference', required=True)
    parser.add_argument('--paid-work', choices=('UNKNOWN', 'RECONCILED'), required=True)
    args = parser.parse_args(argv)
    try:
        value = abandon(args.state_dir, operator=args.operator, reference=args.reference,
                        paid_work=args.paid_work)
        print(json.dumps(dict(status=value['outcome'], inference_requests_this_tick=0)))
        return 0
    except Exception:
        print('{"status":"RESOLUTION_DENIED","inference_requests_this_tick":0}')
        return 4


if __name__ == '__main__':
    raise SystemExit(main())
