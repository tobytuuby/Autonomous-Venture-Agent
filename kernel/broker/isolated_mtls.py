"""Isolated, fail-closed mTLS wrapper for the existing capability broker.

This module does not start a production listener. The caller must explicitly
supply a loopback bind address, certificate paths and certificate pinsets.
"""
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

def tls_context(*, server_cert, server_key, client_ca):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_cert_chain(server_cert, server_key)
    ctx.load_verify_locations(cafile=client_ca)
    return ctx

def handler_for(*, capability_pins, polling_pins, pending=None, acknowledge=None, reservation_actor=None, ceo_reservation_pins=(), ceo_reservation_actor=None, submit=None, status=None, execute=None, cert_mailbox=None, worker_cert_mailbox=None, worker_pins=(), hierarchy=None, worker_reserve=None, worker_execute=None):
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
    class GuardedHandler(ExistingBrokerHandler):
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

        def do_GET(self):
            role = self._role()
            if self.path in ("/v1/certificates/manager/issued",
                             "/v1/certificates/worker/issued"):
                is_worker = self.path == "/v1/certificates/worker/issued"
                if role != ("worker" if is_worker else "poll"):
                    return self._deny()
                mailbox = worker_cert_mailbox if is_worker else cert_mailbox
                if mailbox is None:
                    return self._send(503, {"error": "renewal_unavailable"})
                return self._send(200, {"certificate": mailbox.issued()})
            from agents.ceo.hierarchy_gateway import STATE_PREFIX, ARTIFACT_PREFIX
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

        def do_POST(self):
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
                    result = action(payload)
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
                mailbox = worker_cert_mailbox if is_worker else cert_mailbox
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
            return self._send(405, {"error": "method_not_allowed"})

        def do_DELETE(self):
            return self._send(405, {"error": "method_not_allowed"})
    return GuardedHandler

def isolated_server(*, host, port, server_cert, server_key, client_ca,
                    capability_pins, polling_pins, pending=None, acknowledge=None, reservation_actor=None, ceo_reservation_pins=(), ceo_reservation_actor=None, submit=None, status=None, execute=None, cert_mailbox=None, worker_cert_mailbox=None, worker_pins=(), hierarchy=None, worker_reserve=None, worker_execute=None):
    if host not in ("127.0.0.1", "::1") or port == 8443:
        raise ValueError("isolated test binding only")
    srv = ThreadingHTTPServer((host, port), handler_for(
        capability_pins=set(capability_pins), polling_pins=set(polling_pins),
        pending=pending, acknowledge=acknowledge, reservation_actor=reservation_actor,
        ceo_reservation_pins=ceo_reservation_pins, ceo_reservation_actor=ceo_reservation_actor,
        submit=submit, status=status, execute=execute, cert_mailbox=cert_mailbox, worker_cert_mailbox=worker_cert_mailbox, worker_pins=worker_pins, hierarchy=hierarchy,
        worker_reserve=worker_reserve, worker_execute=worker_execute))
    try:
        srv.socket = tls_context(server_cert=server_cert, server_key=server_key,
                                 client_ca=client_ca).wrap_socket(srv.socket, server_side=True)
    except Exception:
        srv.server_close()
        raise
    return srv
