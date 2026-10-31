"""Real loopback TLS handshake tests with temporary synthetic CA and identities."""
import hashlib
import http.client
import json
import ssl
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from kernel.broker.isolated_mtls import isolated_server, handler_for

def run(*args):
    subprocess.run(["openssl", *map(str,args)], check=True, capture_output=True)

class BrokerMtlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="or010-isolated-")
        d = Path(cls.temp.name)
        cls.paths = {}
        run("req","-x509","-newkey","rsa:2048","-nodes","-days","2",
            "-subj","/CN=Test-CA","-addext","basicConstraints=critical,CA:TRUE","-addext","keyUsage=critical,keyCertSign,cRLSign","-keyout",d/"ca.key","-out",d/"ca.crt")
        for name, eku in (("server","serverAuth"),("cap","clientAuth"),("poll","clientAuth"),("other","clientAuth"),("worker-b","clientAuth"),("worker-a","clientAuth"),("worker-c","clientAuth"),("rollover","clientAuth"),("rogue","clientAuth")):
            key, csr, crt, ext = [d/f"{name}.{e}" for e in ("key","csr","crt","ext")]
            run("req","-new","-newkey","rsa:2048","-nodes","-subj",f"/CN={name}",
                "-keyout",key,"-out",csr)
            ext.write_text(f"subjectAltName=DNS:localhost\\nextendedKeyUsage={eku}\\n".replace("\\n","\n"))
            run("x509","-req","-in",csr,"-CA",d/"ca.crt","-CAkey",d/"ca.key",
                "-CAcreateserial","-out",crt,"-days","2","-extfile",ext)
            cls.paths[name] = (crt,key)
        cls.ca = d/"ca.crt"
        cls.pin = staticmethod(lambda name: hashlib.sha256(ssl.PEM_cert_to_DER_cert(cls.paths[name][0].read_text())).hexdigest())
        cls.srv = isolated_server(host="127.0.0.1",port=0,
          server_cert=cls.paths["server"][0],server_key=cls.paths["server"][1],
          client_ca=cls.ca,capability_pins=[cls.pin("cap")],
          polling_pins=[cls.pin("poll")],pending=lambda: [])
        cls.thread = threading.Thread(target=cls.srv.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def request(self, identity,method,path,body=None, ca=None):
        context = ssl.create_default_context(cafile=str(ca or self.ca))
        if identity:
            crt,key = self.paths[identity]
            context.load_cert_chain(str(crt),str(key))
        c = http.client.HTTPSConnection("localhost",self.srv.server_port,context=context,timeout=3)
        try:
            c.request(method,path,body=body,headers={"Content-Type":"application/json"})
            response = c.getresponse()
            return response.status,json.loads(response.read())
        finally:
            c.close()

    def test_capability_health_unchanged(self):
        self.assertEqual(self.request("cap","GET","/health"),
          (200,{"status":"ok","component":"capability-broker"}))

    def test_worker_and_manager_csr_mailboxes_are_key_bound_and_role_isolated(self):
        from agents.ceo.cert_renewal import ManagerRenewalMailbox, WorkerRenewalMailbox
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            server=isolated_server(host="127.0.0.1",port=0,
                server_cert=self.paths["server"][0],server_key=self.paths["server"][1],
                client_ca=self.ca,capability_pins=[self.pin("cap")],
                polling_pins=[self.pin("poll")],worker_pins=[self.pin("other")],
                cert_mailbox=ManagerRenewalMailbox(d),
                worker_cert_mailbox=WorkerRenewalMailbox(d),
                pending=lambda: [])
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            def call(who,method,path,body=None):
                ctx=ssl.create_default_context(cafile=str(self.ca))
                cert,key=self.paths[who]
                ctx.load_cert_chain(str(cert),str(key))
                conn=http.client.HTTPSConnection("localhost",server.server_port,
                                                 context=ctx,timeout=3)
                try:
                    conn.request(method,path,body=body,
                                 headers={"Content-Type":"application/x-pem-file"})
                    resp=conn.getresponse()
                    return resp.status,json.loads(resp.read())
                finally:
                    conn.close()
            def csr(key,cn,name):
                target=d/(name+".csr")
                run("req","-new","-key",key,"-subj","/CN="+cn,
                    "-out",target)
                return target.read_bytes()
            try:
                worker=csr(self.paths["other"][1],"venture-level2d-worker","worker")
                manager=csr(self.paths["poll"][1],"venture-agents","manager")
                self.assertEqual(call("other","POST","/v1/certificates/worker/csr",worker)[0],200)
                self.assertEqual(call("poll","POST","/v1/certificates/manager/csr",manager)[0],200)
                self.assertEqual(call("poll","GET","/v1/certificates/worker/issued")[0],403)
                self.assertEqual(call("other","GET","/v1/certificates/manager/issued")[0],403)
                self.assertEqual(call("cap","POST","/v1/certificates/worker/csr",worker)[0],403)
                self.assertEqual(call("other","POST","/v1/certificates/worker/csr",manager)[0],400)
                bad_key=csr(self.paths["cap"][1],"venture-level2d-worker","bad")
                self.assertEqual(call("other","POST","/v1/certificates/worker/csr",bad_key)[0],400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


    def test_tls_worker_actor_mapping_inference_and_impersonation(self):
        from agents.ceo import worker_inference as wi
        from agents.ceo.control_plane import load_worker_pins
        from agents.ceo.cert_renewal import WorkerRenewalMailbox
        from tests import test_worker_inference as fixtures
        fx = fixtures.WorkerInferenceTests(methodName="runTest")
        fx.setUp()
        self.addCleanup(fx.doCleanups)
        fx.policy.pop("actor_id")
        fx.policy["actor_ids"] = ["worker-a", "worker-b"]
        # Keep the legacy TLS/Ed25519 trust entry for historical audit use.
        fx.fx.actors["service-worker"] = ("worker", fixtures.fixture.Ed25519PrivateKey.generate().public_key().public_bytes_raw())
        registry = fx.dir / "workers.json"
        registry.write_text(json.dumps(dict(workers={
            "service-worker": self.paths["other"][0].read_text(),
            "worker-a": self.paths["worker-a"][0].read_text(),
            "worker-b": self.paths["worker-b"][0].read_text()})))
        registry.chmod(0o600)
        mapping = load_worker_pins(registry, fx.fx.actors)
        mailboxes = {actor: WorkerRenewalMailbox(fx.dir, actor_id=actor)
                     for actor in mapping.values()}
        server = isolated_server(host="127.0.0.1", port=0,
            server_cert=self.paths["server"][0], server_key=self.paths["server"][1],
            client_ca=self.ca, capability_pins=[self.pin("cap")],
            polling_pins=[self.pin("poll")], worker_pins=tuple(mapping),
            worker_actors=mapping, hierarchy=fx.gateway, worker_cert_mailbox=mailboxes,
            worker_reserve=lambda payload, *, actor: wi.reserve_worker(
                payload, actor=actor, hierarchy=fx.gateway),
            worker_execute=lambda payload, *, actor: wi.execute_worker(
                payload, actor=actor, hierarchy=fx.gateway, provider=fx.provider))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        original = self.srv
        self.srv = server
        try:
            legacy = fx.payload(worker="service-worker", identity="retired-tls")
            self.assertEqual(self.request("other", "POST", wi.RESERVE_PATH,
                json.dumps(legacy["reservation"]))[0], 400)
            self.assertEqual(self.request("other", "POST", wi.EXECUTE_PATH,
                json.dumps(legacy))[0], 400)
            self.assertEqual(fx.ledger_count(), 0)
            self.assertEqual(fx.provider.calls, 0)
            self.assertEqual(self.request("other", "GET", "/v1/certificates/worker/issued")[0], 200)
            a = fx.payload(identity="tls-a")
            b = fx.payload("B", "worker-b", "tls-b")
            for identity in ("cap", "poll", "rogue"):
                self.assertEqual(self.request(identity, "POST", wi.RESERVE_PATH,
                    json.dumps(a["reservation"]))[0], 403)
            # Payload worker_id cannot change the authenticated TLS principal.
            self.assertEqual(self.request("worker-b", "POST", wi.RESERVE_PATH,
                json.dumps(a["reservation"]))[0], 400)
            forged = dict(a["reservation"], worker_id="worker-b")
            self.assertEqual(self.request("worker-b", "POST", wi.RESERVE_PATH,
                json.dumps(forged))[0], 400)
            for who, data in (("worker-a", a), ("worker-b", b)):
                self.assertEqual(self.request(who, "POST", wi.RESERVE_PATH,
                    json.dumps(data["reservation"]))[0], 200)
                self.assertEqual(self.request(who, "POST", wi.EXECUTE_PATH,
                    json.dumps(data))[0], 200)
            self.assertEqual(fx.provider.calls, 2)
            self.assertEqual(self.request("worker-b", "POST", wi.EXECUTE_PATH,
                json.dumps(a))[0], 400)
            changed = json.loads(json.dumps(a))
            changed["request"]["opportunity"]["assignment_id"] = "B"
            self.assertEqual(self.request("worker-a", "POST", wi.EXECUTE_PATH,
                json.dumps(changed))[0], 400)
            # Even a valid sibling signature cannot be relayed under another TLS actor.
            cmd = fx.fx.command("submit", "worker-a", dict(assignment_id="A", units=1))
            self.assertEqual(self.request("worker-b", "POST", "/v1/hierarchy/command",
                json.dumps(dict(command=cmd, signature=fx.fx.sign(cmd, "worker-a"))))[0], 400)
            for n in range(2):
                value = fx.payload("B", "worker-b", "tls-extra-" + str(n))
                self.assertEqual(self.request("worker-b", "POST", wi.RESERVE_PATH,
                    json.dumps(value["reservation"]))[0], 200)
            self.assertEqual(self.request("worker-a", "POST", wi.RESERVE_PATH,
                json.dumps(fx.payload(identity="over-quota")["reservation"]))[0], 400)
            self.assertEqual(fx.ledger_count(), 4)
            # Renewal results stay in the actor's own spool.
            for actor, mailbox in mailboxes.items():
                mailbox.issued = lambda actor=actor: actor
            self.assertEqual(self.request("worker-a", "GET", "/v1/certificates/worker/issued"),
                             (200, {"certificate": "worker-a"}))
            self.assertEqual(self.request("worker-b", "GET", "/v1/certificates/worker/issued"),
                             (200, {"certificate": "worker-b"}))
        finally:
            self.srv = original
            server.shutdown()
            server.server_close()
            thread.join()

    def test_worker_registry_rejects_duplicate_tls_keys_and_unregistered_actors(self):
        from agents.ceo.control_plane import load_worker_pins
        from agents.ceo.escalation_inbox import ROOT
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as tmp:
            path = Path(tmp) / "workers.json"
            actors = {"worker-a": ("worker", b"a"*32), "worker-b": ("worker", b"b"*32)}
            pem = self.paths["other"][0].read_text()
            # Different certificate/pin, same private key, must also fail.
            key = serialization.load_pem_private_key(self.paths["other"][1].read_bytes(), None)
            cert = x509.load_pem_x509_certificate(pem.encode())
            duplicate_key = (x509.CertificateBuilder().subject_name(cert.subject)
                .issuer_name(cert.issuer).public_key(key.public_key()).serial_number(9999)
                .not_valid_before(cert.not_valid_before_utc).not_valid_after(cert.not_valid_after_utc)
                .sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode())
            for workers in ({"worker-a": pem, "worker-b": pem},
                            {"worker-a": pem, "worker-b": duplicate_key},
                            {"unknown": pem}):
                path.write_text(json.dumps(dict(workers=workers)))
                path.chmod(0o600)
                with self.assertRaises(ValueError):
                    load_worker_pins(path, actors)
            with self.assertRaises(ValueError):
                handler_for(capability_pins={self.pin("cap")}, polling_pins={self.pin("poll")},
                    worker_pins=[self.pin("other"), self.pin("worker-b"), self.pin("rogue")])
            with self.assertRaises(ValueError):
                handler_for(capability_pins={self.pin("cap")}, polling_pins={self.pin("poll")},
                    worker_pins=[self.pin("other"), self.pin("worker-b")],
                    worker_actors={self.pin("other"): "worker-a", self.pin("worker-b"): "worker-a"})

    def test_five_pin_cutover_tls_actor_and_renewal_isolation(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from agents.ceo.cert_renewal import WorkerRenewalMailbox
        from agents.ceo.worker_inference import RESERVE_PATH
        identities = {"other": "service-worker", "rollover": "service-worker",
                      "worker-a": "worker-a", "worker-b": "worker-b", "worker-c": "worker-c"}
        mapping = {self.pin(name): actor for name, actor in identities.items()}
        hierarchy = SimpleNamespace(
            actors={actor: ("worker", b"x"*32) for actor in identities.values()}, apply=Mock())
        with tempfile.TemporaryDirectory() as tmp:
            mailboxes = {actor: WorkerRenewalMailbox(Path(tmp), actor_id=actor)
                         for actor in set(identities.values())}
            for actor, mailbox in mailboxes.items():
                mailbox.issued = lambda actor=actor: actor
            server = isolated_server(host="127.0.0.1", port=0,
                server_cert=self.paths["server"][0], server_key=self.paths["server"][1],
                client_ca=self.ca, capability_pins=[self.pin("cap")],
                polling_pins=[self.pin("poll")], worker_pins=tuple(mapping),
                worker_actors=mapping, hierarchy=hierarchy, worker_cert_mailbox=mailboxes,
                worker_reserve=lambda payload, *, actor: {"actor": actor})
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            original = self.srv
            self.srv = server
            try:
                for name, actor in identities.items():
                    with self.subTest(identity=name):
                        self.assertEqual(self.request(name, "GET", "/v1/certificates/worker/issued"),
                                         (200, {"certificate": actor}))
                        # Payload identity cannot select the callback principal.
                        self.assertEqual(self.request(name, "POST", RESERVE_PATH,
                            json.dumps({"worker_id": "impersonated"})), (200, {"actor": actor}))
                        for sibling in set(identities.values()) - {actor}:
                            self.assertEqual(self.request(name, "POST", "/v1/hierarchy/command",
                                json.dumps({"command": {"actor_id": sibling}, "signature": "fake"}))[0], 400)
                        csr = Path(tmp) / (name + ".csr")
                        run("req", "-new", "-key", self.paths[name][1],
                            "-subj", "/CN=venture-level2d-worker", "-out", csr)
                        self.assertEqual(self.request(name, "POST", "/v1/certificates/worker/csr",
                                                      csr.read_bytes())[0], 200)
                        # A sibling TLS certificate cannot submit this key's CSR.
                        sibling_name = "worker-b" if actor != "worker-b" else "other"
                        self.assertEqual(self.request(sibling_name, "POST",
                            "/v1/certificates/worker/csr", csr.read_bytes())[0], 400)
                hierarchy.apply.assert_not_called()
                for name in ("cap", "poll", "rogue"):
                    self.assertEqual(self.request(name, "GET", "/v1/certificates/worker/issued")[0], 403)
                    self.assertEqual(self.request(name, "POST", RESERVE_PATH, "{}")[0], 403)
                # Both legacy TLS keys route into the historical renewal spool.
                self.assertTrue((Path(tmp) / "worker-renewal" / "pending.csr").is_file())
            finally:
                self.srv = original
                server.shutdown()
                server.server_close()
                thread.join()

    def test_worker_registration_limits_and_only_legacy_may_roll_over(self):
        base = dict(capability_pins={"a"*64}, polling_pins={"b"*64})
        invalid = [
            {"c"*64: "service-worker", "d"*64: "service-worker", "e"*64: "service-worker"},
            {"c"*64: "worker-a", "d"*64: "worker-a"},
            {pin*64: "worker-" + str(i) for i, pin in enumerate("cdef0")},
            {pin*64: actor for pin, actor in zip("cdef01",
                ("service-worker", "service-worker", "worker-a", "worker-b", "worker-c", "worker-d"))},
        ]
        for mapping in invalid:
            with self.subTest(actors=list(mapping.values())), self.assertRaises(ValueError):
                handler_for(**base, worker_pins=tuple(mapping), worker_actors=mapping)
        with self.assertRaises(ValueError):
            handler_for(**base, worker_pins=("c"*64, "c"*64))

    def test_polling_isolation(self):
        self.assertEqual(self.request("poll","GET","/v1/assignments/pending"),
                         (200,{"assignments":[]}))
        self.assertEqual(self.request("cap","GET","/v1/assignments/pending")[0],403)
        self.assertEqual(self.request("poll","POST","/v1/capabilities/evaluate",body="{}")[0],403)
        self.assertEqual(self.request("other","GET","/health")[0],403)

    def test_capability_malformed_request(self):
        status, body = self.request("cap","POST","/v1/capabilities/evaluate",body="{")
        self.assertEqual(status,400)
        self.assertEqual(body["decision"],"deny")

    def test_plaintext_rejected(self):
        conn = http.client.HTTPConnection("127.0.0.1",self.srv.server_port,timeout=2)
        with self.assertRaises((OSError,http.client.HTTPException)):
            conn.request("GET","/health")
            conn.getresponse()
        conn.close()

    def test_missing_certificate_denied(self):
        with self.assertRaises((ssl.SSLError,OSError)):
            self.request(None,"GET","/health")

    def test_wrong_ca_denied(self):
        d=Path(self.temp.name)
        run("req","-x509","-newkey","rsa:2048","-nodes","-days","1",
            "-subj","/CN=WrongCA","-keyout",d/"wrong.key","-out",d/"wrong.crt")
        with self.assertRaises((ssl.SSLError,OSError)):
            self.request("cap","GET","/health",ca=d/"wrong.crt")

    def test_wrong_methods_and_query(self):
        self.assertEqual(self.request("poll","PUT","/v1/assignments/pending")[0],405)
        self.assertNotEqual(self.request("poll","GET","/v1/assignments/pending?x=1")[0],200)
        self.assertEqual(self.request("poll","GET","/health")[0],403)

    def test_bad_pin_configuration(self):
        with self.assertRaises(ValueError):
            handler_for(capability_pins=set(),polling_pins={self.pin("poll")})

    def test_hostname_mismatch(self):
        context = ssl.create_default_context(cafile=str(self.ca))
        crt,key=self.paths["cap"]
        context.load_cert_chain(str(crt),str(key))
        conn=http.client.HTTPSConnection("127.0.0.1",self.srv.server_port,context=context,timeout=3)
        with self.assertRaises(ssl.SSLCertVerificationError):
            conn.request("GET","/health")
        conn.close()

    def test_certificate_rollover_and_revocation_pinset(self):
        # CA-valid replacement is refused until explicitly placed in the pinset.
        self.assertEqual(self.request("other","GET","/health")[0],403)
        pins={self.pin("cap"),self.pin("other")}
        handler=handler_for(capability_pins=pins,polling_pins={self.pin("poll")})
        self.assertTrue(issubclass(handler,object))
        pins.remove(self.pin("cap"))
        self.assertNotIn(self.pin("cap"),pins)
        # This validates pinset update logic, not an active listener reload.

    def test_non_executing_poll_no_fallback(self):
        self.assertEqual(self.request("poll","GET","/v1/assignments/pending"),(200,{"assignments":[]}))
        self.assertEqual(self.request("cap","POST","/v1/capabilities/evaluate",body="{}")[0],400)
        self.assertEqual(self.request("other","POST","/v1/capabilities/evaluate",body="{}")[0],403)

    def test_recovery_after_tls_rejection(self):
        with self.assertRaises((ssl.SSLError,OSError)):
            self.request(None,"GET","/health")
        self.assertEqual(self.request("cap","GET","/health")[0],200)

    def test_wire_capability_decision_states(self):
        from unittest.mock import patch
        from kernel.broker.server import broker
        from tests.test_broker import req
        for policy_allowed, expected in ((False, "deny"), (True, "escalate")):
            with self.subTest(expected=expected), patch.object(broker, "policy_evaluator", lambda _: policy_allowed):
                status, response = self.request("cap", "POST", "/v1/capabilities/evaluate",
                                               body=json.dumps(req()))
                self.assertEqual(status, 200)
                self.assertEqual(response["decision"], expected)
                self.assertIsNone(response["grant"])
        self.assertEqual(self.request("poll","POST","/v1/capabilities/evaluate",
                                      body=json.dumps(req()))[0],403)

    def test_expired_real_certificate_and_live_pin_rollover(self):
        from datetime import datetime, timedelta, timezone
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
        d=Path(self.temp.name)
        ca_key=serialization.load_pem_private_key((d/"ca.key").read_bytes(),password=None)
        ca_cert=x509.load_pem_x509_certificate(self.ca.read_bytes())
        def signed_client(name, before, after):
            key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
            cert=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,name)]))
                  .issuer_name(ca_cert.subject).public_key(key.public_key())
                  .serial_number(x509.random_serial_number())
                  .not_valid_before(before).not_valid_after(after)
                  .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),critical=False)
                  .sign(ca_key,hashes.SHA256()))
            keyfile=d/f"{name}.key"
            certfile=d/f"{name}.crt"
            keyfile.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.TraditionalOpenSSL,serialization.NoEncryption()))
            certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            return str(certfile),str(keyfile),hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest()
        now=datetime.now(timezone.utc)
        expired=signed_client("expired",(now-timedelta(days=3)),(now-timedelta(days=1)))
        replacement=signed_client("replacement",(now-timedelta(minutes=5)),(now+timedelta(days=2)))
        def request_port(port, crt, key):
            ctx=ssl.create_default_context(cafile=str(self.ca))
            ctx.load_cert_chain(crt,key)
            conn=http.client.HTTPSConnection("localhost",port,context=ctx,timeout=3)
            try:
                conn.request("GET","/health")
                resp=conn.getresponse()
                return resp.status
            finally:
                conn.close()
        oldpin=self.pin("cap")
        for pins, old_status, new_status in (
            ([oldpin],200,403),
            ([oldpin,replacement[2]],200,200),
            ([replacement[2]],403,200)
        ):
            server=isolated_server(host="127.0.0.1",port=0,
                server_cert=self.paths["server"][0],server_key=self.paths["server"][1],
                client_ca=self.ca,capability_pins=pins,polling_pins=[self.pin("poll")],pending=lambda: [])
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                self.assertEqual(request_port(server.server_port,*self.paths["cap"]),old_status)
                self.assertEqual(request_port(server.server_port,*replacement[:2]),new_status)
                with self.assertRaises((ssl.SSLError,OSError)):
                    request_port(server.server_port,*expired[:2])
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_secure_recovery_rehearsal(self):
        # Simulate a failed cutover, fail closed, then recover to authenticated TLS.
        server=isolated_server(host="127.0.0.1",port=0,
            server_cert=self.paths["server"][0],server_key=self.paths["server"][1],
            client_ca=self.ca,capability_pins=[self.pin("cap")],
            polling_pins=[self.pin("poll")],pending=lambda: [])
        port=server.server_port
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            context=ssl.create_default_context(cafile=str(self.ca))
            context.load_cert_chain(*map(str,self.paths["cap"]))
            conn=http.client.HTTPSConnection("localhost",port,context=context,timeout=2)
            conn.request("GET","/health")
            self.assertEqual(conn.getresponse().status,200)
            conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        # No listener (not plaintext rollback) after failure/shutdown.
        with self.assertRaises(OSError):
            conn=http.client.HTTPConnection("127.0.0.1",port,timeout=1)
            conn.request("GET","/health")
            conn.getresponse()
        recovered=isolated_server(host="127.0.0.1",port=0,
            server_cert=self.paths["server"][0],server_key=self.paths["server"][1],
            client_ca=self.ca,capability_pins=[self.pin("cap")],
            polling_pins=[self.pin("poll")],pending=lambda: [])
        t=threading.Thread(target=recovered.serve_forever,daemon=True)
        t.start()
        try:
            ctx=ssl.create_default_context(cafile=str(self.ca))
            ctx.load_cert_chain(*map(str,self.paths["cap"]))
            conn=http.client.HTTPSConnection("localhost",recovered.server_port,context=ctx,timeout=2)
            conn.request("GET","/health")
            self.assertEqual(conn.getresponse().status,200)
            conn.close()
        finally:
            recovered.shutdown()
            recovered.server_close()
            t.join()
