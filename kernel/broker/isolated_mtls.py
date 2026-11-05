"""Isolated, fail-closed mTLS wrapper for the existing capability broker.

This module does not start a production listener. The caller must explicitly
supply a loopback bind address, certificate paths and certificate pinsets.
"""
from contextlib import contextmanager, nullcontext
import hashlib
import json
import re
from agents.ceo.cross_vm_transport import _object, MAX_ACK
from agents.ceo.cross_vm_poll_client import ACK_PATH
from agents.ceo.provider_reservation import RESERVATION_PATH, MAX_RESERVATION
import ssl
from http.server import ThreadingHTTPServer
from kernel.broker.server import Handler as ExistingBrokerHandler

POLL_PATH = "/v1/assignments/pending"
CEO_SUBMIT_PATH = "/v1/assignments/submit"
EXECUTE_PATH = "/v1/inference/execute"
CEO_STATUS_PREFIX = "/v1/assignments/status/"
CAP_PATH = "/v1/capabilities/evaluate"


class MaintenanceDenied(RuntimeError):
    """Configured admission is closed, unsafe, or cannot be established."""


class MaintenanceAdmission:
    """Host-local persistent admission and flock drain; never an execution ledger.

    See docs/p1-04-broker-maintenance-c1-v1.0.md for provisioning and release.
    Each operation opens independent file descriptions (including per thread).
    """

    def __init__(self, path, identity):
        import os
        from pathlib import Path
        self.path = Path(path)
        if (not self.path.is_absolute() or str(self.path) != path
                or ".." in self.path.parts):
            raise MaintenanceDenied("absolute canonical maintenance path required")
        try:
            self.identity = tuple(int(n) for n in identity.split(":"))
        except (AttributeError, ValueError):
            raise MaintenanceDenied("maintenance inode identity required") from None
        if len(self.identity) != 6 or any(n < 0 for n in self.identity):
            raise MaintenanceDenied("maintenance inode identity required")
        self.uid = os.geteuid()
        # Validate without changing persistent admission.
        for active in (False, True):
            os.close(self._open(active))

    def _open(self, active=False):
        import os
        import stat
        name = self.path.name + (".active" if active else "")
        directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        fd = None
        try:
            for part in self.path.parent.parts[1:]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=directory)
                os.close(directory)
                directory = child
                info = os.fstat(directory)
                if info.st_uid not in (0, self.uid):
                    raise MaintenanceDenied("unsafe maintenance ancestor")
            info = os.fstat(directory)
            if (info.st_uid != self.uid or stat.S_IMODE(info.st_mode) != 0o700
                    or (info.st_dev, info.st_ino) != self.identity[4:6]):
                raise MaintenanceDenied("private maintenance directory required")
            fd = os.open(name, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=directory)
            info = os.fstat(fd)
            offset = 2 if active else 0
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != self.uid
                    or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
                    or (info.st_dev, info.st_ino) != self.identity[offset:offset+2]
                    or (active and info.st_size != 0)):
                raise MaintenanceDenied("unsafe maintenance inode")
            result, fd = fd, None
            return result
        except OSError:
            raise MaintenanceDenied("maintenance control unavailable") from None
        finally:
            if fd is not None:
                os.close(fd)
            os.close(directory)

    def _check(self, control):
        import os
        # Rewalk the pathname after locking; never operate on a detached inode.
        for active in (False, True):
            os.close(self._open(active))
        state = os.pread(control, 16, 0)
        if state not in (b"OPEN\n", b"CLOSED\n"):
            raise MaintenanceDenied("malformed maintenance state")
        return state

    @staticmethod
    def _deadline(timeout):
        import math
        import time
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 <= timeout <= 300:
            raise MaintenanceDenied("maintenance timeout must be between 0 and 300 seconds")
        return time.monotonic() + timeout

    @staticmethod
    def _lock(fd, mode, deadline):
        import fcntl
        import time
        while True:
            try:
                fcntl.flock(fd, mode | fcntl.LOCK_NB)
                return
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise MaintenanceDenied("maintenance lock/drain timeout") from None
                time.sleep(min(0.01, max(0, deadline - time.monotonic())))
            except OSError:
                raise MaintenanceDenied("maintenance lock unavailable") from None

    @staticmethod
    def _write(control, state):
        import os
        try:
            if os.pwrite(control, state, 0) != len(state):
                raise OSError("short maintenance write")
            os.ftruncate(control, len(state))
            os.fsync(control)
        except OSError:
            # Attempt to invalidate OPEN on write/fsync failure.
            # Best effort CLOSED also covers a partial write. Failed storage
            # cannot establish drain/release success and requires operator HOLD.
            try:
                os.pwrite(control, b"CLOSED\n", 0)
                os.ftruncate(control, 7)
                os.fsync(control)
            except OSError:
                pass
            raise MaintenanceDenied("maintenance persistence failed") from None

    @contextmanager
    def request(self):
        import os
        import fcntl
        control = self._open()
        active = None
        try:
            self._lock(control, fcntl.LOCK_EX, self._deadline(0.25))
            if self._check(control) != b"OPEN\n":
                raise MaintenanceDenied("maintenance closed")
            active = self._open(True)
            self._lock(active, fcntl.LOCK_SH, self._deadline(0))
            self._check(control)
            # Admission and activity lock acquired under the same mutex as close.
            fcntl.flock(control, fcntl.LOCK_UN)
            yield
        finally:
            if active is not None:
                os.close(active)
            os.close(control)

    @contextmanager
    def drain(self, timeout=30):
        """Persist CLOSED first, then yield only with exclusive drained activity.

        CLOSED survives timeout, exceptions, operator death and context exit.
        No automatic reopen. Keep this context through maintenance operations.
        """
        import os
        import fcntl
        deadline = self._deadline(timeout)
        control = self._open()
        active = None
        try:
            self._lock(control, fcntl.LOCK_EX, deadline)
            self._check(control)
            self._write(control, b"CLOSED\n")
            fcntl.flock(control, fcntl.LOCK_UN)
            active = self._open(True)
            self._lock(active, fcntl.LOCK_EX, deadline)
            self._lock(control, fcntl.LOCK_EX, deadline)
            if self._check(control) != b"CLOSED\n":
                raise MaintenanceDenied("closure changed during drain")
            fcntl.flock(control, fcntl.LOCK_UN)
            yield
        finally:
            if active is not None:
                os.close(active)
            os.close(control)

    def release(self, timeout=0):
        """Explicit local safe release: require valid CLOSED and zero activity."""
        import os
        import fcntl
        deadline = self._deadline(timeout)
        control = self._open()
        active = None
        try:
            self._lock(control, fcntl.LOCK_EX, deadline)
            if self._check(control) != b"CLOSED\n":
                raise MaintenanceDenied("explicit release requires CLOSED")
            active = self._open(True)
            self._lock(active, fcntl.LOCK_EX, deadline)
            self._check(control)
            self._write(control, b"OPEN\n")
        finally:
            if active is not None:
                os.close(active)
            os.close(control)

def tls_context(*, server_cert, server_key, client_ca):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_cert_chain(server_cert, server_key)
    ctx.load_verify_locations(cafile=client_ca)
    return ctx

def handler_for(*, capability_pins, polling_pins, pending=None, acknowledge=None, reservation_actor=None, ceo_reservation_pins=(), ceo_reservation_actor=None, submit=None, status=None, execute=None, cert_mailbox=None, worker_cert_mailbox=None, worker_pins=(), worker_actors=None, hierarchy=None, worker_reserve=None, worker_execute=None, ceo_execute=None, maintenance=None):
    """Pin DER certificate SHA256 per authorized role, never trust HTTP headers."""
    if not capability_pins or not polling_pins:
        raise ValueError("both identity pinsets required")
    if not all(isinstance(s, str) and len(s) == 64 and
               all(c in "0123456789abcdef" for c in s)
               for s in (*capability_pins, *polling_pins, *ceo_reservation_pins, *worker_pins)):
        raise ValueError("malformed fingerprint")
    if (set(capability_pins) & set(polling_pins) or set(capability_pins) & set(ceo_reservation_pins)
            or set(polling_pins) & set(ceo_reservation_pins)
            or set(worker_pins) & (set(capability_pins) | set(polling_pins) | set(ceo_reservation_pins))):
        raise ValueError("role pinsets must be disjoint")
    if bool(ceo_reservation_pins) != bool(ceo_reservation_actor):
        raise ValueError("CEO reservation identity incomplete")
    if reservation_actor is not None and (not isinstance(reservation_actor, str) or not reservation_actor):
        raise ValueError("reservation actor pin required")
    if ceo_reservation_pins and (not isinstance(ceo_reservation_actor, str)
                                 or not ceo_reservation_actor
                                 or ceo_reservation_actor == reservation_actor):
        raise ValueError("distinct CEO reservation actor required")
    # Legacy current/rollover certificates share one actor. New workers each
    # require a distinct pin; request data never selects the authenticated actor.
    worker_actors = dict(worker_actors) if worker_actors is not None else (
        {pin: "service-worker" for pin in worker_pins} if len(worker_pins) <= 2 else {})
    from collections import Counter
    from agents.ceo.escalation_inbox import identifier
    counts = Counter(worker_actors.values())
    if (set(worker_actors) != set(worker_pins) or len(worker_pins) != len(worker_actors)
            or len(worker_actors) > 5 or len(counts) > 4
            or any(count > (2 if actor == "service-worker" else 1)
                   for actor, count in counts.items())):
        raise ValueError("unique worker pin to actor registration required")
    for actor in worker_actors.values():
        identifier(actor)
        if hierarchy is not None and hierarchy.actors.get(actor, (None,))[0] != "worker":
            raise ValueError("registered worker role required")
    if len(counts) > 1 and worker_cert_mailbox is not None and not isinstance(worker_cert_mailbox, dict):
        raise ValueError("separate worker renewal mailboxes required")

    class GuardedHandler(ExistingBrokerHandler):
        def _worker_actor(self):
            if not isinstance(self.connection, ssl.SSLSocket):
                return None
            cert = self.connection.getpeercert(binary_form=True)
            return worker_actors.get(hashlib.sha256(cert).hexdigest()) if cert else None

        def _worker_mailbox(self):
            if isinstance(worker_cert_mailbox, dict):
                return worker_cert_mailbox.get(self._worker_actor())
            return worker_cert_mailbox

        def _role(self):
            if not isinstance(self.connection, ssl.SSLSocket):
                return None
            cert = self.connection.getpeercert(binary_form=True)
            if not cert:
                return None
            fingerprint = hashlib.sha256(cert).hexdigest()
            if fingerprint in worker_pins:
                return "worker"
            if fingerprint in ceo_reservation_pins:
                return "quota-ceo"
            if fingerprint in polling_pins:
                return "poll"
            if fingerprint in capability_pins:
                return "capability"
            return None

        def _deny(self):
            self._send(403, {"error": "identity_denied"})

        def handle_one_request(self):
            # Acquire before parsing headers/body, including unknown methods and
            # inherited HTTP errors. Initialize fields needed for an early 503.
            self.requestline = ""
            self.request_version = "HTTP/1.1"
            self.command = None
            return self._admitted(super().handle_one_request)

        def _admitted(self, callback):
            if getattr(self, "_admission_held", False):
                return callback()
            # The lease includes identity rejection, body reads, every callback,
            # inherited capability evaluation, durable commits and response I/O.
            lease = maintenance.request() if maintenance is not None else nullcontext()
            try:
                lease.__enter__()
            except MaintenanceDenied:
                self.close_connection = True
                return self._send(503, {"error": "maintenance_denied"})
            self._admission_held = True
            try:
                return callback()
            finally:
                self._admission_held = False
                lease.__exit__(None, None, None)

        def do_GET(self):
            return self._admitted(self._get)

        def do_POST(self):
            return self._admitted(self._post)

        def _get(self):
            role = self._role()
            if self.path in ("/v1/certificates/manager/issued",
                             "/v1/certificates/worker/issued"):
                is_worker = self.path == "/v1/certificates/worker/issued"
                if role != ("worker" if is_worker else "poll"):
                    return self._deny()
                mailbox = self._worker_mailbox() if is_worker else cert_mailbox
                if mailbox is None:
                    return self._send(503, {"error": "renewal_unavailable"})
                return self._send(200, {"certificate": mailbox.issued()})
            from agents.ceo.hierarchy_gateway import STATE_PREFIX, ARTIFACT_PREFIX
            from agents.ceo.hierarchy_gateway import WORKER_COUNTS_PREFIX
            if self.path.startswith(WORKER_COUNTS_PREFIX):
                if role != "quota-ceo":
                    return self._deny()
                if hierarchy is None:
                    return self._send(503, {"error": "hierarchy_unavailable"})
                try:
                    return self._send(200, hierarchy.worker_research_counts(
                        self.path[len(WORKER_COUNTS_PREFIX):]))
                except (ValueError, TypeError, KeyError):
                    return self._send(400, {"error": "research_counts_denied"})
                except Exception:
                    return self._send(503, {"error": "research_counts_unavailable"})
            if self.path == '/v1/hierarchy/research':
                if role not in ('quota-ceo','poll','worker'):
                    return self._deny()
                if hierarchy is None:
                    return self._send(503, {'error':'hierarchy_unavailable'})
                try:
                    return self._send(200, {'research':hierarchy.research_list()})
                except Exception:
                    return self._send(503, {'error':'research_state_unavailable'})
            if self.path.startswith(STATE_PREFIX):
                if role not in ("quota-ceo", "poll", "worker"):
                    return self._deny()
                if hierarchy is None:
                    return self._send(503, {"error": "hierarchy_unavailable"})
                try:
                    state = hierarchy.state(self.path[len(STATE_PREFIX):])
                    return self._send(200, {"state": state})
                except ValueError:
                    return self._send(400, {"error": "hierarchy_state_denied"})
                except Exception:
                    return self._send(503, {"error": "hierarchy_state_unavailable"})
            if self.path.startswith(ARTIFACT_PREFIX):
                if role not in ("quota-ceo", "poll", "worker"):
                    return self._deny()
                if hierarchy is None:
                    return self._send(503, {"error": "hierarchy_unavailable"})
                try:
                    content = hierarchy.artifact(self.path[len(ARTIFACT_PREFIX):], role=role)
                    return self._send(200, {"content": content})
                except ValueError:
                    return self._send(400, {"error": "artifact_denied"})
                except Exception:
                    return self._send(503, {"error": "artifact_unavailable"})
            if self.path == POLL_PATH:
                if role != "poll":
                    return self._deny()
                if pending is None:
                    return self._send(503, {"error": "polling_unavailable"})
                return self._send(200, {"assignments": pending()})
            if self.path.startswith(CEO_STATUS_PREFIX):
                if role != "quota-ceo":
                    return self._deny()
                if status is None:
                    return self._send(503, {"error": "status_unavailable"})
                task_id = self.path[len(CEO_STATUS_PREFIX):]
                if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,119}", task_id):
                    return self._send(400, {"error": "invalid_task"})
                try:
                    record = status(task_id)
                except Exception:
                    return self._send(503, {"error": "status_unavailable"})
                return self._send(200, {"record": record})
            if self.path == "/health" and role == "capability":
                return super().do_GET()
            return self._deny() if role is None or self.path == "/health" else self._send(404, {"error": "not_found"})

        def _post(self):
            from agents.ceo.ceo_broker import PROOF_PATH, EXECUTE_PATH as CEO_EXECUTE_PATH, ceo_proof
            if self.path in (PROOF_PATH, CEO_EXECUTE_PATH):
                if self._role() != "quota-ceo":
                    return self._deny()
                if hierarchy is None or (self.path == CEO_EXECUTE_PATH and ceo_execute is None):
                    return self._send(503, {"error": "ceo_inference_unavailable"})
                try:
                    lengths = self.headers.get_all("Content-Length", [])
                    if len(lengths) != 1 or self.headers.get("Transfer-Encoding") is not None:
                        raise ValueError("bounded CEO length required")
                    length = int(lengths[0])
                    if not 0 < length <= 16000:
                        raise ValueError("CEO request bound")
                    self.connection.settimeout(5)
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ValueError("incomplete CEO request")
                    payload = json.loads(raw, object_pairs_hook=_object)
                    if self.path == PROOF_PATH:
                        result = ceo_proof(payload, actor=ceo_reservation_actor, hierarchy=hierarchy)
                    else:
                        result = {"result": ceo_execute(payload, actor=ceo_reservation_actor)}
                    if len(json.dumps(result, separators=(",", ":")).encode()) > 16300:
                        raise ValueError("CEO response bound")
                    return self._send(200, result)
                except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
                    return self._send(400, {"error": "ceo_inference_denied"})
                except Exception:
                    return self._send(503, {"error": "ceo_inference_unavailable"})
            from agents.ceo.hierarchy_gateway import COMMAND_PATH, ARTIFACT_PATH, MAX_COMMAND
            from agents.ceo.worker_inference import RESERVE_PATH as WORKER_RESERVE_PATH, EXECUTE_PATH as WORKER_EXECUTE_PATH
            if self.path in (WORKER_RESERVE_PATH, WORKER_EXECUTE_PATH):
                if self._role() != "worker":
                    return self._deny()
                action = worker_reserve if self.path == WORKER_RESERVE_PATH else worker_execute
                if action is None:
                    return self._send(503, {"error": "worker_inference_unavailable"})
                try:
                    lengths = self.headers.get_all("Content-Length", [])
                    if len(lengths) != 1 or self.headers.get("Transfer-Encoding"):
                        raise ValueError("worker length denied")
                    length = int(lengths[0])
                    if not 0 < length <= 16000:
                        raise ValueError("bounded worker request required")
                    self.connection.settimeout(5)
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ValueError("incomplete Worker inference")
                    payload = json.loads(raw, object_pairs_hook=_object)
                    result = action(payload, actor=self._worker_actor())
                    if len(json.dumps(result,separators=(",",":")).encode()) > 16000:
                        raise ValueError("oversized Worker response")
                    return self._send(200, result)
                except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
                    return self._send(400, {"error": "worker_inference_denied"})
                except Exception:
                    return self._send(503, {"error": "worker_inference_unavailable"})
            from agents.ceo.hierarchy_gateway import BOOTSTRAP_PREPARE_PATH, BOOTSTRAP_COMMIT_PATH
            if self.path in (BOOTSTRAP_PREPARE_PATH, BOOTSTRAP_COMMIT_PATH):
                if self._role() != "quota-ceo":
                    return self._deny()
                if hierarchy is None:
                    return self._send(503, {"error": "hierarchy_unavailable"})
                try:
                    lengths = self.headers.get_all("Content-Length", [])
                    if len(lengths) != 1 or self.headers.get("Transfer-Encoding") is not None:
                        raise ValueError("signed bootstrap length required")
                    length = int(lengths[0])
                    if not 0 < length <= 16000:
                        raise ValueError("bounded bootstrap request required")
                    self.connection.settimeout(5)
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ValueError("incomplete hierarchy bootstrap")
                    payload = json.loads(raw, object_pairs_hook=_object)
                    if self.path == BOOTSTRAP_PREPARE_PATH:
                        return self._send(200, {"handoff": hierarchy.bootstrap_prepare(payload)})
                    return self._send(200, {"state": hierarchy.bootstrap_commit(payload)})
                except (ValueError,TypeError,KeyError,UnicodeError,RecursionError):
                    return self._send(400, {"error": "hierarchy_bootstrap_denied"})
                except Exception:
                    return self._send(503, {"error": "hierarchy_bootstrap_unavailable"})
            if self.path in (COMMAND_PATH, ARTIFACT_PATH):
                role = self._role()
                if role not in ("quota-ceo", "poll", "worker"):
                    return self._deny()
                if hierarchy is None:
                    return self._send(503, {"error": "hierarchy_unavailable"})
                try:
                    lengths = self.headers.get_all("Content-Length", [])
                    if len(lengths) != 1 or self.headers.get("Transfer-Encoding") is not None:
                        raise ValueError("bounded signed hierarchy request required")
                    length = int(lengths[0])
                    if not 0 < length <= MAX_COMMAND:
                        raise ValueError("hierarchy request too large")
                    self.connection.settimeout(5)
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ValueError("incomplete signed request")
                    payload = json.loads(raw, object_pairs_hook=_object)
                    if self.path == COMMAND_PATH:
                        if role == "worker" and payload["command"]["actor_id"] != self._worker_actor():
                            raise ValueError("TLS worker and signed command actor mismatch")
                        return self._send(200, {"state": hierarchy.apply(payload, role=role)})
                    return self._send(200, {"stored": hierarchy.store(payload, role=role)})
                except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
                    return self._send(400, {"error": "hierarchy_transition_denied"})
                except Exception:
                    return self._send(503, {"error": "hierarchy_transition_unavailable"})
            if self.path in ("/v1/certificates/manager/csr",
                             "/v1/certificates/worker/csr"):
                is_worker = self.path == "/v1/certificates/worker/csr"
                if self._role() != ("worker" if is_worker else "poll"):
                    return self._deny()
                mailbox = self._worker_mailbox() if is_worker else cert_mailbox
                if mailbox is None:
                    return self._send(503, {"error": "renewal_unavailable"})
                try:
                    lengths = self.headers.get_all("Content-Length", [])
                    if len(lengths) != 1 or self.headers.get("Transfer-Encoding"):
                        raise ValueError("CSR length denied")
                    length = int(lengths[0])
                    if not 1 <= length <= 8192:
                        raise ValueError("CSR bound")
                    self.connection.settimeout(5)
                    data = self.rfile.read(length)
                    if len(data) != length:
                        raise ValueError("incomplete CSR")
                    # Renewal is confined to the exact TLS-authenticated
                    # role key. A valid certificate may not mint a successor
                    # for an unrelated private key or cross-role identity.
                    from cryptography import x509
                    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
                    csr = x509.load_pem_x509_csr(data)
                    peer = x509.load_der_x509_certificate(
                        self.connection.getpeercert(binary_form=True))
                    public = lambda key: key.public_bytes(
                        Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
                    if public(csr.public_key()) != public(peer.public_key()):
                        raise ValueError("CSR key must match authenticated certificate")
                    mailbox.submit(data)
                    return self._send(200, {"accepted": True})
                except (ValueError, TypeError, IndexError):
                    return self._send(400, {"error": "csr_denied"})
                except Exception:
                    return self._send(503, {"error": "renewal_unavailable"})
            if self.path == CEO_SUBMIT_PATH:
                if self._role() != "quota-ceo":
                    return self._deny()
                if submit is None:
                    return self._send(503, {"error": "submission_unavailable"})
                try:
                    lengths = self.headers.get_all("Content-Length", [])
                    if len(lengths) != 1 or self.headers.get("Transfer-Encoding") is not None:
                        raise ValueError("bounded submission required")
                    length = int(lengths[0])
                    if not 0 < length <= MAX_ACK:
                        raise ValueError("submission size denied")
                    self.connection.settimeout(5)
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ValueError("incomplete submission")
                    envelope = json.loads(raw, object_pairs_hook=_object)
                    created = submit(envelope)
                    if type(created) is not bool:
                        raise ValueError("invalid broker submission result")
                    return self._send(200, {"accepted": True, "duplicate": not created,
                                            "task_id": envelope["body"]["task_id"]})
                except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
                    return self._send(400, {"error": "submission_denied"})
                except Exception:
                    return self._send(503, {"error": "submission_unavailable"})
            if self.path == EXECUTE_PATH:
                if self._role() != "poll":
                    return self._deny()
                if execute is None:
                    return self._send(503, {"error": "provider_execution_unavailable"})
                try:
                    lengths = self.headers.get_all("Content-Length", [])
                    if len(lengths) != 1 or self.headers.get("Transfer-Encoding") is not None:
                        raise ValueError("bounded inference length required")
                    length = int(lengths[0])
                    if not 0 < length <= 16384:
                        raise ValueError("inference length denied")
                    self.connection.settimeout(5)
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ValueError("incomplete inference")
                    payload = json.loads(raw, object_pairs_hook=_object)
                    result = execute(payload)
                    if len(json.dumps(result, separators=(",", ":")).encode()) > 16300:
                        raise ValueError("oversized inference response")
                    return self._send(200, {"result": result})
                except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
                    return self._send(400, {"error": "inference_denied"})
                except Exception:
                    return self._send(503, {"error": "inference_unavailable"})
            if self.path == RESERVATION_PATH:
                role = self._role()
                if role not in ("poll", "quota-ceo"):
                    return self._deny()
                if (reservation_actor if role == "poll" else ceo_reservation_actor) is None:
                    return self._send(503, {"error": "reservation_unavailable"})
                try:
                    lengths = self.headers.get_all("Content-Length", [])
                    if len(lengths) != 1 or self.headers.get("Transfer-Encoding") is not None:
                        raise ValueError("bounded length required")
                    length = int(lengths[0])
                    if not 0 < length <= MAX_RESERVATION:
                        raise ValueError("reservation length denied")
                    self.connection.settimeout(5)
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ValueError("incomplete reservation")
                    payload = json.loads(raw, object_pairs_hook=_object)
                    from agents.ceo.provider_reservation import reserve_exchange
                    result = reserve_exchange(payload, actor=(reservation_actor if role == "poll" else ceo_reservation_actor),
                        role=("manager" if role == "poll" else "ceo"))
                except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
                    return self._send(400, {"error": "reservation_denied"})
                except Exception:
                    return self._send(503, {"error": "reservation_unavailable"})
                return self._send(200, result)
            if self.path == ACK_PATH:
                if self._role() != "poll":
                    return self._deny()
                if acknowledge is None:
                    return self._send(503, {"error": "acknowledgement_unavailable"})
                try:
                    lengths = self.headers.get_all("Content-Length", [])
                    if len(lengths) != 1 or self.headers.get("Transfer-Encoding") is not None:
                        raise ValueError("explicit bounded length required")
                    length = int(lengths[0])
                    if not 0 < length <= MAX_ACK:
                        raise ValueError("invalid acknowledgement length")
                    self.connection.settimeout(5)
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ValueError("incomplete acknowledgement")
                    envelope = json.loads(raw, object_pairs_hook=_object)
                    result = acknowledge(envelope)
                except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
                    return self._send(400, {"error": "acknowledgement_denied"})
                except Exception:
                    return self._send(503, {"error": "acknowledgement_unavailable"})
                return self._send(200, result)
            if self.path == CAP_PATH and self._role() == "capability":
                return super().do_POST()
            return self._deny() if self.path == CAP_PATH or self._role() is None else self._send(404, {"error": "not_found"})

        def do_PUT(self):
            return self._admitted(lambda: self._send(405, {"error": "method_not_allowed"}))

        def do_DELETE(self):
            return self._admitted(lambda: self._send(405, {"error": "method_not_allowed"}))
    return GuardedHandler

def isolated_server(*, host, port, server_cert, server_key, client_ca,
                    capability_pins, polling_pins, pending=None, acknowledge=None, reservation_actor=None, ceo_reservation_pins=(), ceo_reservation_actor=None, submit=None, status=None, execute=None, cert_mailbox=None, worker_cert_mailbox=None, worker_pins=(), worker_actors=None, hierarchy=None, worker_reserve=None, worker_execute=None, ceo_execute=None, maintenance=None):
    if host not in ("127.0.0.1", "::1") or port == 8443:
        raise ValueError("isolated test binding only")
    srv = ThreadingHTTPServer((host, port), handler_for(
        capability_pins=set(capability_pins), polling_pins=set(polling_pins),
        pending=pending, acknowledge=acknowledge, reservation_actor=reservation_actor,
        ceo_reservation_pins=ceo_reservation_pins, ceo_reservation_actor=ceo_reservation_actor,
        submit=submit, status=status, execute=execute, cert_mailbox=cert_mailbox, worker_cert_mailbox=worker_cert_mailbox, worker_pins=worker_pins, worker_actors=worker_actors, hierarchy=hierarchy,
        worker_reserve=worker_reserve, worker_execute=worker_execute, ceo_execute=ceo_execute, maintenance=maintenance))
    try:
        srv.socket = tls_context(server_cert=server_cert, server_key=server_key,
                                 client_ca=client_ca).wrap_socket(srv.socket, server_side=True)
    except Exception:
        srv.server_close()
        raise
    return srv
