"""Schedule one fixed advisory workflow, never a fresh venture on each tick.

Only a pristine state directory permits up to three provider requests, once.
Existing state permits durable replay only. Interrupted/failed requests require
operator investigation; no timer retry can dispatch another request.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from agents.ceo.agent import CEOAgent, ResponseValidationError
from agents.ceo.durable_state import DurableDecisionStore
from agents.ceo.gates import CertificationGateError
from agents.ceo.provider import ModelProviderError
from agents.ceo.venture_exercise import SYSTEM, configured_provider, inside_root, run_exercise
from kernel.p6.registry import canonical
from kernel.synthetic_venture_store import SyntheticVentureStore

FILES = ("workflow.sqlite", "workflow.decisions.sqlite", "workflow.decisions.jsonl",
         "report.json", "attempt.json", "status.json", "runner.lock")


def now():
    return datetime.now(timezone.utc).isoformat()


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_json(path, value, *, exclusive=False):
    """Persist before dispatch; interrupted writes cannot silently authorize retry."""
    data = (canonical(value) + "\n").encode()
    target = path if exclusive else path.with_suffix(path.suffix + ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW
    flags |= os.O_EXCL if exclusive else os.O_TRUNC
    fd = os.open(target, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if not exclusive:
        os.replace(target, path)
    sync_directory(path.parent)


class BoundedProvider:
    def __init__(self, provider, marker, allow_inference):
        self.provider = provider
        self.marker = marker
        self.allow_inference = allow_inference
        self.calls = 0
        for key in ("model_family", "endpoint", "model"):
            setattr(self, key, getattr(provider, key))

    def __call__(self, request, tools):
        if not self.allow_inference or self.calls >= 3 or tools:
            raise ModelProviderError("scheduled workflow permits durable replay only")
        if self.calls == 0:
            write_json(self.marker, {"started_at": now(), "workflow": "venture-exercise-v4",
                                    "maximum_requests": 3}, exclusive=True)
        self.calls += 1
        return self.provider(request, ())


def run(state_dir, gate_file, environ=None):
    raw = Path(state_dir).absolute()
    # Reject aliases to other project artifacts, including the original run.
    if any(p.is_symlink() for p in (raw, *raw.parents)):
        raise ValueError("state directory must not contain symlinks")
    state = inside_root(raw)
    if state == inside_root("."):
        raise ValueError("dedicated state directory required")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in FILES:
        path = state / name
        if path.is_symlink() or (path.exists() and
                                 (not path.is_file() or path.stat().st_nlink != 1)):
            raise ValueError("regular unaliased state files required")
    lock_fd = os.open(state / "runner.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, "r+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0, {"status": "BUSY", "inference_requests_this_tick": 0}
        started = now()
        summary = {"started_at": started, "workflow": "venture-exercise-v4",
                   "external_action_count": 0, "inference_requests_this_tick": 0,
                   "artifacts": list(FILES[:-1]),
                   "ai_inference_independently_verified": False}
        provider = None
        decisions = None
        try:
            env = dict(os.environ if environ is None else environ)
            env["CEO_KERNEL_GATE_FILE"] = str(inside_root(gate_file))
            configured = configured_provider(env, required=True)
            # Never infer on imported, partially written or previously attempted state.
            pristine = not any((state / name).exists() for name in FILES[:-1])
            provider = BoundedProvider(configured, state / "attempt.json", pristine)
            decisions = DurableDecisionStore(state / "workflow.decisions.sqlite")
            if not decisions.verify_chain():
                raise ValueError("durable event chain invalid")
            agent = CEOAgent(provider, SYSTEM, state / "workflow.decisions.jsonl",
                             durable_store=decisions, advisory_only=True,
                             runner_version="venture-exercise-v4")
            with SyntheticVentureStore(state / "workflow.sqlite") as store:
                result = run_exercise(store, ceo_agent=agent)
            write_json(state / "report.json", result)
            summary.update(status="COMPLETED" if provider.calls else "REPLAYED",
                           exercise_status=result["status"],
                           report_sha256=hashlib.sha256((state / "report.json").read_bytes()).hexdigest())
            code = 0
        except CertificationGateError:
            summary["status"] = "GATE_DENIED"
            code = 3
        except ResponseValidationError as exc:
            summary.update(status="RESPONSE_DENIED", reason=exc.reason_code)
            code = 4
        except ModelProviderError:
            summary["status"] = "PROVIDER_OR_REPLAY_DENIED"
            code = 2
        except Exception:
            # No remote bodies, environment, exception text or traceback in logs.
            summary["status"] = "STATE_DENIED"
            code = 4
        finally:
            if decisions is not None:
                decisions.close()
        summary.update(finished_at=now(),
                       inference_requests_this_tick=provider.calls if provider else 0)
        write_json(state / "status.json", summary)
        return code, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", default="artifacts/scheduled-ceo")
    parser.add_argument("--gate-file", default="infrastructure/venture-ceo-kernel-gate.runtime.json")
    args = parser.parse_args()
    try:
        code, summary = run(args.state_dir, args.gate_file)
    except Exception:
        code, summary = 4, {"status": "LOCAL_PATH_DENIED", "inference_requests_this_tick": 0}
    print(canonical(summary))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
