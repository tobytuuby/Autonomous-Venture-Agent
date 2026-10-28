"""Linux containment for fixed local workers; fail closed if unavailable."""
import ctypes
import ctypes.util
import errno
import os
from pathlib import Path
import resource

def contain(inputs, output):
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    libc = ctypes.CDLL(None, use_errno=True)
    def check(result):
        if result < 0:
            raise OSError(ctypes.get_errno(), "worker containment unavailable")
        return result
    check(libc.prctl(38, 1, 0, 0, 0))  # PR_SET_NO_NEW_PRIVS
    # Landlock: deny filesystem access except runtime, inputs and this attempt.
    abi = check(libc.syscall(444, 0, 0, 1))
    if abi < 3:
        raise RuntimeError("Landlock ABI >=3 required")
    handled = (1 << 15) - 1
    class Ruleset(ctypes.Structure):
        _fields_ = [("access", ctypes.c_uint64)]
    class Rule(ctypes.Structure):
        _pack_ = 1
        _fields_ = [("access", ctypes.c_uint64), ("parent", ctypes.c_int32)]
    fd = check(libc.syscall(444, ctypes.byref(Ruleset(handled)), 8, 0))
    read = 1 | 4 | 8  # execute, read file, read directory
    try:
        for path, access in [(p, read) for p in
                             ("/usr", "/lib", "/lib64", str(inputs))] + [(str(output), handled),
                                                              ("/dev/null", 2 | 4)]:
            if not Path(path).exists():
                continue
            parent = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                check(libc.syscall(445, fd, 1, ctypes.byref(Rule(access, parent)), 0))
            finally:
                os.close(parent)
        check(libc.syscall(446, fd, 0))
    finally:
        os.close(fd)
    # seccomp blocks network even for subprocesses and native libraries.
    lib = ctypes.CDLL(ctypes.util.find_library("seccomp") or "libseccomp.so.2")
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    ctx = lib.seccomp_init(0x7fff0000)
    if not ctx:
        raise RuntimeError("seccomp unavailable")
    try:
        for name in ("socket", "socketpair", "connect", "bind", "listen",
                     "accept", "accept4", "ptrace", "process_vm_readv",
                     "process_vm_writev", "mount", "io_uring_setup", "io_uring_enter",
                     "io_uring_register"):
            nr = lib.seccomp_syscall_resolve_name(name.encode())
            if nr >= 0:
                check(lib.seccomp_rule_add(ctx, 0x50000 | errno.EPERM, nr, 0))
        check(lib.seccomp_load(ctx))
    finally:
        lib.seccomp_release(ctx)
