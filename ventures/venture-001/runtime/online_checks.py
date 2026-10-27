"""Trusted ephemeral loopback HTTP acceptance; no remote targets or deployment.
Usage: python3 online_checks.py SOURCE OUTPUT [--browser]
Only synthetic accounts. Each WSGI request executes inside sandbox_checks.py.
"""
import argparse
import base64
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
import http.client
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading

CODE = Path(__file__).resolve().parent
ROOT = CODE.parents[2]
MAX_BODY = 65536

@contextmanager
def private_server(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if (not source.is_relative_to(ROOT) or not output.is_relative_to(ROOT)
            or not (source / "app.py").is_file() or source == output
            or source in output.parents or output in source.parents):
        raise ValueError("backend source and separate in-project output required")
    output.mkdir(parents=True, exist_ok=True)
    snapshot, data = output / "http-inputs", output / "http-data"
    snapshot.mkdir()
    data.mkdir()
    (snapshot / "app").mkdir()
    files = [p for p in source.rglob("*") if p.is_file() or p.is_symlink()]
    if len(files) > 16 or sum(p.stat().st_size for p in files if not p.is_symlink()) > 196608:
        raise ValueError("source count/total byte bound")
    for p in files:
        if p.is_symlink():
            raise ValueError("source symlink denied")
        if p.is_file():
            if p.stat().st_size > 131072:
                raise ValueError("source byte bound")
            dest = snapshot / "app" / p.relative_to(source)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dest)
    shutil.copyfile(CODE / "wsgi_request.py", snapshot / "checks.py")
    count = 0

    class Handler(BaseHTTPRequestHandler):
        timeout = 5
        def log_message(self, *args):
            pass  # never log synthetic credentials, cookies or response data
        def handle_request(self):
            nonlocal count
            count += 1
            self.connection.settimeout(5)
            host = "127.0.0.1:" + str(self.server.server_port)
            if count > 150 or self.headers.get("Host") != host:
                self.send_error(403)
                return
            if "?" in self.path or not self.path.startswith("/") or self.path.startswith("//"):
                self.send_error(400)
                return
            if not self.path.startswith("/api/"):
                name = "index.html" if self.path == "/" else self.path[1:]
                if (self.command != "GET" or "/" in name or name.startswith(".")
                        or Path(name).suffix not in (".html", ".css", ".js")):
                    self.send_error(404)
                    return
                asset = snapshot / "app" / name
                if not asset.is_file():
                    self.send_error(404)
                    return
                body = asset.read_bytes()
                mime = {".html": "text/html", ".css": "text/css", ".js": "text/javascript"}[asset.suffix]
                self.send_response(200)
                self.send_header("Content-Type", mime + "; charset=utf-8")
                self.send_header("Content-Security-Policy",
                                 "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; form-action 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 <= length <= MAX_BODY or self.headers.get("Transfer-Encoding"):
                    raise ValueError("body bound")
                request = {
                    "method": self.command, "path": self.path, "port": str(self.server.server_port),
                    "host": host, "origin": self.headers.get("Origin", ""),
                    "cookie": self.headers.get("Cookie", ""),
                    "content_type": self.headers.get("Content-Type", ""),
                    "body": base64.b64encode(self.rfile.read(length)).decode("ascii"),
                }
                command = [sys.executable, "-I", "-S", "-B", str(CODE / "sandbox_checks.py"),
                           str(CODE), str(snapshot), str(data)]
                with tempfile.TemporaryFile(dir=output) as response, tempfile.TemporaryFile(dir=output) as errors:
                    proc = subprocess.run(command, input=json.dumps(request).encode(),
                                          stdout=response, stderr=errors, cwd=data,
                                          env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}, timeout=12)
                    if proc.returncode:
                        raise ValueError("contained backend failed")
                    response.seek(0)
                    raw = response.read(524289)
                    if len(raw) > 524288:
                        raise ValueError("response bound")
                    result = json.loads(raw)
                body = base64.b64decode(result["body"], validate=True)
                self.send_response(result["status"])
                for key, value in result["headers"]:
                    if key.lower() not in ("connection", "transfer-encoding", "content-length", "server"):
                        self.send_header(key, value)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)
            except (ValueError, OSError, KeyError, subprocess.TimeoutExpired):
                self.send_error(500, "Contained backend failed; no raw request or credential logs")
        do_GET = do_POST = do_PUT = do_DELETE = handle_request

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

class Client:
    def __init__(self, port):
        self.port, self.cookie = port, ""
    def request(self, method, path, value=None, *, origin=True, csv=False):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        body = value if csv else json.dumps(value) if value is not None else None
        headers = {"Content-Type": "text/csv" if csv else "application/json", "Cookie": self.cookie}
        if origin:
            headers["Origin"] = "http://127.0.0.1:" + str(self.port)
        try:
            conn.request(method, path, body, headers)
            response = conn.getresponse()
            raw = response.read(262145)
            if len(raw) > 262144:
                raise AssertionError("response bound")
            cookies = response.getheaders()
            for key, val in cookies:
                if key.lower() == "set-cookie":
                    self.cookie = val.split(";", 1)[0]
            return response.status, raw, cookies
        finally:
            conn.close()

def acceptance(port):
    a, b, anonymous = Client(port), Client(port), Client(port)
    def call(client, method, path, value=None, expected=(200,), **kwargs):
        status, body, headers = client.request(method, path, value, **kwargs)
        assert status in expected, method + " " + path + " returned " + str(status)
        return body, headers
    def items(client):
        return json.loads(call(client, "GET", "/api/items")[0])
    creds = {"username": "synthetic-alpha", "password": "Synthetic-test-only-Alpha-924!"}
    call(anonymous, "GET", "/api/items", expected=(401, 403))
    call(a, "POST", "/api/register", creds, expected=(403,), origin=False)
    _, headers = call(a, "POST", "/api/register", creds, expected=(201,))
    cookies = [v.lower() for k, v in headers if k.lower() == "set-cookie"]
    assert cookies and all("httponly" in c and "samesite=strict" in c for c in cookies), "session flags"
    call(b, "POST", "/api/register", {"username": "synthetic-beta", "password": "Synthetic-test-only-Beta-924!"}, expected=(201,))
    print("PASS: anonymous/Origin denial and independent tenant sessions", flush=True)
    item = {"name": "Synthetic clay", "on_hand": 10, "inbound": 0, "reorder_point": 10,
            "target": 20, "pack_size": 5, "pack_price": 3}
    call(a, "POST", "/api/items", item, expected=(201,))
    rows = items(a)
    assert len(rows) == 1 and rows[0]["name"] == item["name"], "server inventory missing"
    identity = str(rows[0]["id"])
    assert items(b) == [], "tenant read leak"
    call(b, "PUT", "/api/items/" + identity, item, expected=(403, 404))
    call(b, "DELETE", "/api/items/" + identity, expected=(403, 404))
    call(a, "PUT", "/api/items/" + identity, {**item, "pack_size": 0}, expected=(400, 422))
    assert items(a) == rows, "invalid update mutated inventory"
    call(a, "PUT", "/api/items/" + identity, {**item, "name": "Synthetic updated"})
    print("PASS: durable CRUD/input validation and cross-tenant write denial", flush=True)
    reorder = json.loads(call(a, "GET", "/api/reorder")[0])
    match = next(r for r in reorder if str(r["id"]) == identity)
    assert (match["packs"], match["quantity"], match["estimate"]) == (2, 10, 6), "reorder math"
    print("PASS: server pack-aware reorder", flush=True)
    old_cookie = a.cookie
    call(a, "POST", "/api/logout", expected=(200, 204))
    stale = Client(port)
    stale.cookie = old_cookie
    call(stale, "GET", "/api/items", expected=(401, 403))
    a = Client(port)
    call(a, "POST", "/api/login", creds)
    assert items(a)[0]["name"] == "Synthetic updated", "new-client/process continuity"
    print("PASS: logout revocation and fresh-client login continuity across backend processes", flush=True)
    backup = json.loads(call(a, "GET", "/api/backup")[0])
    assert "synthetic-beta" not in json.dumps(backup) and creds["password"] not in json.dumps(backup), "unsafe backup"
    exported = call(a, "GET", "/api/export")[0].decode()
    assert "Synthetic updated" in exported, "export missing inventory"
    before = items(a)
    call(a, "POST", "/api/import", "bad,header\nbroken,row\n", csv=True, expected=(400, 422))
    assert items(a) == before, "invalid import was not atomic"
    call(a, "DELETE", "/api/items/" + identity, expected=(200, 204))
    assert items(a) == [], "delete failed"
    call(a, "POST", "/api/import", exported, csv=True)
    assert items(a)[0]["name"] == "Synthetic updated", "CSV round trip"
    for row in items(a):
        call(a, "DELETE", "/api/items/" + str(row["id"]), expected=(200, 204))
    call(a, "POST", "/api/restore", backup)
    assert items(a)[0]["name"] == "Synthetic updated", "backup restore failed"
    assert items(b) == [], "restore leaked across tenants"
    print("PASS: CSV atomic rejection/round trip and tenant backup/restore", flush=True)
    recovery = Client(port)
    known, _ = call(recovery, "POST", "/api/recover", {"username": creds["username"]})
    unknown, _ = call(recovery, "POST", "/api/recover", {"username": "nonexistent"})
    assert known == unknown and not recovery.cookie, "recovery enumerates or authenticates"
    call(recovery, "GET", "/api/items", expected=(401, 403))
    retained_cookie = a.cookie
    call(a, "DELETE", "/api/account", expected=(200, 204))
    a.cookie = retained_cookie
    call(a, "GET", "/api/items", expected=(401, 403))
    call(a, "POST", "/api/login", creds, expected=(401, 403))
    assert items(b) == [], "account deletion crossed tenants"
    print("PASS: generic recovery and account deletion/session revocation; retained-backup privacy requires security review", flush=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--browser", action="store_true")
    args = parser.parse_args()
    try:
        with private_server(args.source, args.output) as port:
            acceptance(port)
            if args.browser:
                import os
                node = os.environ.get("STUDIO_NODE")
                if not node:
                    raise ValueError("browser runtime missing")
                result = subprocess.run([node, str(CODE / "online_browser.cjs"), str(port)],
                                        env=dict(os.environ), timeout=90)
                if result.returncode:
                    return result.returncode
        print("SUMMARY: local HTTP gates passed; remote staging/deployment NOT performed")
        return 0
    except (AssertionError, ValueError, OSError, StopIteration, KeyError, subprocess.TimeoutExpired) as exc:
        # Assertions only contain gate/path/status, never credentials or raw body.
        print("FAIL: online acceptance " + (str(exc) if isinstance(exc, AssertionError) else type(exc).__name__))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
