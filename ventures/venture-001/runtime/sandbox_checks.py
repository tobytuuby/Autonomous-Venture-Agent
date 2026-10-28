"""Execute generated Python checks with no network, secrets, shell or children."""
import ctypes
import errno
from pathlib import Path
import resource
import runpy
import sys

sys.path.insert(0, sys.argv[1])
from containment import contain

source, output = Path(sys.argv[2]), Path(sys.argv[3])
lib = ctypes.CDLL("libseccomp.so.2", use_errno=True)
lib.seccomp_init.restype = ctypes.c_void_p
lib.seccomp_init.argtypes = [ctypes.c_uint32]
lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
lib.seccomp_load.argtypes = [ctypes.c_void_p]
lib.seccomp_release.argtypes = [ctypes.c_void_p]
lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
contain(source, output)
resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024,) * 2)
ctx = lib.seccomp_init(0x7fff0000)
if not ctx:
    raise RuntimeError("check process containment unavailable")
try:
    for name in ("fork", "vfork", "clone", "clone3", "execve", "execveat"):
        nr = lib.seccomp_syscall_resolve_name(name.encode())
        if nr >= 0 and lib.seccomp_rule_add(ctx, 0x50000 | errno.EPERM, nr, 0) < 0:
            raise RuntimeError("check process containment unavailable")
    if lib.seccomp_load(ctx) < 0:
        raise RuntimeError("check process containment unavailable")
finally:
    lib.seccomp_release(ctx)
sys.argv = [str(source / "checks.py"), str(source / "app")]
runpy.run_path(sys.argv[0], run_name="__main__")
