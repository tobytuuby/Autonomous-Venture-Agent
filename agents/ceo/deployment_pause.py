"""CEO-only cooperative deployment exclusion; never deployment authority.

The lock must be preprovisioned in a private, service-owned directory and must
never be replaced/unlinked during use. All participating CEO processes must use
the same inode. No broker/Manager/Worker lock or persisted workflow is changed.
"""
from contextlib import contextmanager
import errno
import fcntl
import os
import stat

from agents.ceo.escalation_inbox import ROOT, inside_root


@contextmanager
def lease(path, *, exclusive=False):
    """Nonblocking lease. False means an active cycle/pause prevents admission.

    The exclusive holder must remain alive throughout preflight, upgrade or code
    rollback and verification. This helper performs none of those operations.
    Process death releases the lock; it is not a durable maintenance switch.
    """
    path = inside_root(path)
    # ROOT is the existing approved trust anchor, not an isolation claim. A
    # deployment must independently attest its permissions and adopted inode.
    parent = path.parent
    if parent == ROOT or parent.stat().st_uid != os.geteuid() or parent.stat().st_mode & 0o077:
        raise ValueError("private service-owned deployment lock parent required")
    while parent != ROOT:
        info = parent.stat()
        if info.st_uid not in (0, os.geteuid()) or info.st_mode & 0o022:
            raise ValueError("deployment lock parent is writable by another user")
        parent = parent.parent
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    acquired = False
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != os.geteuid() or info.st_mode & 0o077
                or info.st_size != 0):
            raise ValueError("private preprovisioned empty deployment lock required")
        try:
            fcntl.flock(fd, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
                        | fcntl.LOCK_NB)
            acquired = True
        except OSError as exc:
            if exc.errno not in (errno.EACCES, errno.EAGAIN):
                raise
        current = path.stat()
        if (current.st_dev, current.st_ino, current.st_nlink) != (
                info.st_dev, info.st_ino, 1):
            raise ValueError("deployment lock identity changed")
        yield acquired
    finally:
        if acquired:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


@contextmanager
def cycle(config):
    """Opt-in CEO poll admission; a paused poll performs no broker request."""
    if "deployment_lock" not in config:
        yield True
        return
    if config.get("role") != "ceo" or config.get("actor_id") != "service-ceo":
        raise ValueError("deployment pause is CEO-only")
    with lease(config["deployment_lock"]) as admitted:
        yield admitted


def preflight(path):
    """Probe exclusion, never promote advisory exclusion into deployment proof."""
    reasons = [
        "INSTALLED_CEO_LOCK_ADOPTION_AND_INODE_NOT_VERIFIED",
        "CONTROL_AND_AGENTS_STATE_COVERAGE_NOT_VERIFIED",
        "SHARED_BROKER_DRAIN_NOT_PROVEN",
        "DURABLE_LEDGER_ROLLBACK_PROTECTION_NOT_PROVEN",
        "CURRENT_LOADED_CODE_AUTHORITY_AND_REVIEW_GATES_REQUIRED",
    ]
    result = dict(decision="DENY", deployment_allowed=False, resume_verified=False,
                  classification="COOPERATIVE_CEO_EXCLUSION_ONLY", blockers=reasons,
                  ceo_exclusion_observed=False)
    try:
        with lease(path, exclusive=True) as admitted:
            result["ceo_exclusion_observed"] = admitted
            if not admitted:
                reasons.insert(0, "CEO_CYCLE_OR_PAUSE_ACTIVE")
    except Exception:
        reasons.insert(0, "INVALID_OR_UNAVAILABLE_DEPLOYMENT_LOCK")
    return result
