"""Opt-in same-host role admission using the existing C1 durable control.

No provisioning or automatic release. All participants for one UID on one host
must pin the same private files. Other UIDs/hosts require independent gates.
"""
from contextlib import contextmanager
from functools import wraps
import os
import re
import threading

_HELD = threading.local()


def configured_gate(config):
    """Validate the complete source config; absence alone preserves legacy use."""
    if "maintenance_admission" not in config:
        return None
    from kernel.broker.isolated_mtls import MaintenanceAdmission, MaintenanceDenied
    value = config["maintenance_admission"]
    if (type(value) is not dict or set(value) != {"control", "identity"}
            or type(value["control"]) is not str
            or type(value["identity"]) is not str
            or re.fullmatch(r"(?:0|[1-9][0-9]*)(?::(?:0|[1-9][0-9]*)){5}",
                            value["identity"]) is None):
        raise MaintenanceDenied("exact maintenance control and inode identity required")
    return MaintenanceAdmission(value["control"], value["identity"])


@contextmanager
def admission(config):
    gate = configured_gate(config)
    if gate is None:
        yield
        return
    # Synchronous nested role helpers finish under the original admission even
    # after CLOSED is persisted. Never transfer a lease via config or to another
    # thread/process. A fork does not inherit admission authority.
    key = (os.getpid(), str(gate.path), gate.identity)
    held = getattr(_HELD, "keys", ())
    if key in held:
        yield
        return
    with gate.request():
        _HELD.keys = (*held, key)
        try:
            yield
        finally:
            _HELD.keys = held


def admitted(function):
    """Protect config-first direct helpers through their final local writes."""
    @wraps(function)
    def guarded(config, *args, **kwargs):
        with admission(config):
            return function(config, *args, **kwargs)
    return guarded
