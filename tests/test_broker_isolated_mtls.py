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
