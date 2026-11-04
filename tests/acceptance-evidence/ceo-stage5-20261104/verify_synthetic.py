"""Run bounded synthetic tests with non-loopback socket connections denied."""
import ipaddress
import runpy
import socket
import sys
import unittest

original_connect = socket.socket.connect

def loopback_connect(sock, address):
    if sock.family in (socket.AF_INET, socket.AF_INET6):
        try:
            allowed = ipaddress.ip_address(address[0]).is_loopback
        except ValueError:
            allowed = address[0] == "localhost"
        if not allowed:
            raise AssertionError("External network connection forbidden in synthetic validation")
    return original_connect(sock, address)

socket.socket.connect = loopback_connect
if sys.argv[1] == "--profile":
    sys.argv = [sys.argv[2]]
    runpy.run_path(sys.argv[0], run_name="__main__")
else:
    unittest.main(module=None, argv=[sys.argv[0]] + sys.argv[1:], verbosity=2)
