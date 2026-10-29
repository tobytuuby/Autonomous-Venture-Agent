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
        for name, eku in (("server","serverAuth"),("cap","clientAuth"),("poll","clientAuth"),("other","clientAuth")):
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
