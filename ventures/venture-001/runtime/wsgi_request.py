"""Trusted per-request adapter, executed as checks.py by sandbox_checks.py.
Generated WSGI code inherits existing no-network/no-child/filesystem containment.
"""
import base64
import contextlib
import io
import json
from pathlib import Path
import runpy
import sys

app_dir = Path(sys.argv[1])
sys.path.insert(0, str(app_dir))
request = json.loads(sys.stdin.buffer.read(100000))
body = base64.b64decode(request["body"], validate=True)
env = {
    "REQUEST_METHOD": request["method"], "PATH_INFO": request["path"],
    "QUERY_STRING": "", "SERVER_NAME": "127.0.0.1", "SERVER_PORT": request["port"],
    "SERVER_PROTOCOL": "HTTP/1.1", "wsgi.version": (1, 0),
    "wsgi.url_scheme": "http", "wsgi.input": io.BytesIO(body),
    "wsgi.errors": sys.stderr, "wsgi.multithread": False,
    "wsgi.multiprocess": True, "wsgi.run_once": True,
    "CONTENT_LENGTH": str(len(body)), "CONTENT_TYPE": request["content_type"],
    "HTTP_HOST": request["host"], "HTTP_ORIGIN": request["origin"],
    "HTTP_COOKIE": request["cookie"], "STUDIO_DATA_DIR": str(Path.cwd()),
}
result = {}
def start_response(status, headers, exc_info=None):
    if result or exc_info:
        raise ValueError("duplicate/error response")
    code = int(status.split()[0])
    if not 100 <= code <= 599 or not isinstance(headers, list):
        raise ValueError("invalid WSGI status/headers")
    if len(headers) > 32 or any(not isinstance(k, str) or not isinstance(v, str)
                               or "\r" in k + v or "\n" in k + v
                               or len(k + v) > 8192 for k, v in headers):
        raise ValueError("invalid WSGI headers")
    result.update(status=code, headers=headers)
    return lambda data: (_ for _ in ()).throw(ValueError("WSGI write unsupported"))

with contextlib.redirect_stdout(sys.stderr):
    application = runpy.run_path(str(app_dir / "app.py"))["application"]
    response = application(env, start_response)
    chunks, size = [], 0
    try:
        for chunk in response:
            if not isinstance(chunk, bytes):
                raise ValueError("WSGI bytes required")
            size += len(chunk)
            if size > 262144:
                raise ValueError("response byte bound")
            chunks.append(chunk)
    finally:
        if hasattr(response, "close"):
            response.close()
if "status" not in result:
    raise ValueError("missing WSGI start_response")
result["body"] = base64.b64encode(b"".join(chunks)).decode("ascii")
print(json.dumps(result))
