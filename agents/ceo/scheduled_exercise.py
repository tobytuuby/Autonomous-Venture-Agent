"""Hourly bounded advisory progression over a preserved synthetic bootstrap.

Bootstrap permits three calls once; subsequent hourly queue cycles permit two.
Interrupted inference fails closed without automatic paid retries.
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
INTAKE_FILES = ("escalations.sqlite", "inbox-status.json")
QUEUE_FILES = ("queue.started.json", "queue.sqlite", "queue.decisions.sqlite",
               "queue.decisions.jsonl")


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


def run(state_dir, gate_file, environ=None, *, queue=True, cycle=None, intake_only=False,
        escalation_only=False, escalation_grant=None, operator_public_key=None):
    raw = Path(state_dir).absolute()
    # Reject aliases to other project artifacts, including the original run.
    if any(p.is_symlink() for p in (raw, *raw.parents)):
        raise ValueError("state directory must not contain symlinks")
    state = inside_root(raw)
    if state == inside_root("."):
        raise ValueError("dedicated state directory required")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    from agents.ceo.scheduled_escalation import FILES as ESCALATION_FILES
    from agents.ceo.queue_recovery import RECORD
    for name in (*FILES, *QUEUE_FILES, *INTAKE_FILES, *ESCALATION_FILES, RECORD,
                 *(name + suffix for name in ("workflow.sqlite", "workflow.decisions.sqlite",
                    "queue.sqlite", "queue.decisions.sqlite", "escalations.sqlite",
                    "escalation.decisions.sqlite") for suffix in ("-journal", "-wal", "-shm"))):
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
                   "artifacts": list(FILES[:-1]) + (list(QUEUE_FILES) if queue else []) + list(INTAKE_FILES) + list(ESCALATION_FILES) + [RECORD],
                   "ai_inference_independently_verified": False}
        from agents.ceo.scheduled_intake import ingest_pending
        intake_code, summary["inbox"] = ingest_pending(state)
        if intake_only:
            summary.update(status="INTAKE_ONLY" if not intake_code else "INTAKE_DENIED",
                           finished_at=now(), ceo_work_performed=False,
                           queue_status="NOT_RUN", artifacts=list(INTAKE_FILES))
            write_json(state / "inbox-status.json", summary)
            return intake_code, summary
        from agents.ceo.scheduled_escalation import process_pending
        env = dict(os.environ if environ is None else environ)
        if intake_code:
            escalation_code, summary["escalation"] = 4, {"status": "ESCALATION_INTAKE_DENIED",
                "inference_requests_this_tick": 0, "ceo_work_performed": False}
        else:
            escalation_code, summary["escalation"] = process_pending(
                state, inside_root(gate_file), env, grant_file=escalation_grant,
                operator_public_key=operator_public_key)
        escalation_calls = summary["escalation"]["inference_requests_this_tick"]
        # An explicit escalation invocation never enters bootstrap/legacy queue.
        # Any supplied grant also isolates this tick's budget, including denial.
        if escalation_only or escalation_grant is not None:
            summary.update(status=summary["escalation"]["status"], finished_at=now(),
                           inference_requests_this_tick=escalation_calls, queue_status="NOT_RUN")
            write_json(state / "inbox-status.json", summary)
            missing = summary["escalation"]["status"] == "ESCALATION_AUTHORIZATION_REQUIRED"
            return escalation_code or intake_code or (3 if missing else 0), summary
        provider = None
        decisions = None
        try:
            env["CEO_KERNEL_GATE_FILE"] = str(inside_root(gate_file))
            configured = configured_provider(env, required=True)
            # Never infer on imported, partially written or previously attempted state.
            pristine = not any((state / name).exists() for name in (*FILES[:-1], *QUEUE_FILES))
            provider = BoundedProvider(configured, state / "attempt.json", pristine)
            decisions = DurableDecisionStore(state / "workflow.decisions.sqlite")
            if not decisions.verify_chain():
                raise ValueError("durable event chain invalid")
            agent = CEOAgent(provider, SYSTEM, state / "workflow.decisions.jsonl",
                             durable_store=decisions, advisory_only=True,
                             runner_version="venture-exercise-v4")
            with SyntheticVentureStore(state / "workflow.sqlite") as store:
                result = run_exercise(store, ceo_agent=agent)
            queue_code, queue_summary = 0, {}
            if queue and not provider.calls:
                from agents.ceo.advisory_queue import advance
                marker = state / "queue.started.json"
                database = state / "queue.sqlite"
                if not marker.exists():
                    if any((state / name).exists() for name in QUEUE_FILES):
                        raise ValueError("partial imported queue state")
                    write_json(marker, {"started_at": now(), "version": "advisory-queue-v1"},
                               exclusive=True)
                elif not database.exists():
                    raise ValueError("interrupted queue initialization")
                queue_code, queue_summary = advance(state, configured, result, cycle)
                summary.update(queue_summary)
                if queue_code:
                    summary.update(finished_at=now())
                    write_json(state / "status.json", summary)
                    return queue_code, summary
            write_json(state / "report.json", result)
            summary.update(status=queue_summary.get("status", "COMPLETED" if provider.calls else "REPLAYED"),
                           exercise_status=result["status"],
                           report_sha256=hashlib.sha256((state / "report.json").read_bytes()).hexdigest())
            summary.update(queue_summary)
            code = queue_code
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
                       inference_requests_this_tick=(provider.calls if provider else 0) +
                       summary.get("inference_requests_this_tick", 0))
        write_json(state / "status.json", summary)
        return code or intake_code or escalation_code, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", default="artifacts/scheduled-ceo")
    parser.add_argument("--gate-file", default="infrastructure/venture-ceo-kernel-gate.runtime.json")
    parser.add_argument("--intake-only", action="store_true",
                        help="Local inbox intake only; never configure or call inference")
    parser.add_argument("--escalation-only", action="store_true",
                        help="Independent advisory escalation lane; never run legacy queue")
    parser.add_argument("--escalation-grant", help="Operator-signed one-call budget grant inside project")
    parser.add_argument("--operator-public-key", help="Trusted operator public key file (hex); no enrollment")
    args = parser.parse_args()
    if args.intake_only and (args.escalation_only or args.escalation_grant or args.operator_public_key):
        parser.error("intake-only cannot process escalation")
    if bool(args.escalation_grant) != bool(args.operator_public_key):
        parser.error("both grant and trusted public key are required")
    try:
        from agents.ceo.queue_recovery import regular
        key = None
        if args.operator_public_key:
            with regular(Path(args.operator_public_key)).open("rb") as stream:
                key = bytes.fromhex(stream.read(65).decode().strip())
        code, summary = run(args.state_dir, args.gate_file, intake_only=args.intake_only,
                            escalation_only=args.escalation_only,
                            escalation_grant=Path(args.escalation_grant) if args.escalation_grant else None,
                            operator_public_key=key)
    except Exception:
        code, summary = 4, {"status": "LOCAL_PATH_DENIED", "inference_requests_this_tick": 0}
    print(canonical(summary))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
