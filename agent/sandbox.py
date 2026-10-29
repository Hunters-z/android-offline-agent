"""
Sandbox ketat: blokir SEMUA akses network di level interpreter.
Agent tidak bisa keluar ke internet — bahkan jika prompt-nya mencoba.
Import modul ini SEBELUM modul lain apa pun.
"""
import socket, builtins, os, sys

_blocked_msg = "[SANDBOX] Akses network diblokir. Agent ini offline-total."

def _blocked(*a, **k):
    raise OSError(_blocked_msg)

# 1) Socket: blokir network LUAR, izinkan loopback 127.0.0.1 (UI lokal tetap jalan)
import _socket as _csock
_LOOPBACK = ("127.0.0.1", "localhost", "::1", "0.0.0.0")

class _GuardedSocket(socket.socket):
    def connect(self, address):
        host = address[0] if isinstance(address, (tuple, list)) else str(address)
        if host in _LOOPBACK or str(host).startswith("127."):
            return super().connect(address)
        raise OSError(_blocked_msg)
    def connect_ex(self, address):
        host = address[0] if isinstance(address, (tuple, list)) else str(address)
        if host in _LOOPBACK or str(host).startswith("127."):
            return super().connect_ex(address)
        raise OSError(_blocked_msg)

socket.socket = _GuardedSocket
_orig_create_connection = socket.create_connection
def _guard_create_connection(address, *a, **k):
    host = address[0] if isinstance(address, (tuple, list)) else str(address)
    if host in _LOOPBACK or str(host).startswith("127.") or str(host) in ALLOWED_HOSTS:
        return _orig_create_connection(address, *a, **k)
    raise OSError(_blocked_msg)
socket.create_connection = _guard_create_connection
# host API yang diizinkan saat mode cloud (diatur runtime oleh server.py)
ALLOWED_HOSTS = set()
def allow_host(h): ALLOWED_HOSTS.add(str(h))

def _guard_getaddrinfo(host, *a, **k):
    h = str(host)
    if h not in _LOOPBACK and not h.startswith("127.") and h not in ALLOWED_HOSTS:
        raise OSError(_blocked_msg)
    return _csock.getaddrinfo(h, *a, **k)
socket.getaddrinfo = _guard_getaddrinfo
socket.gethostbyname = _blocked

# 2) urllib/requests/httpx/urllib3 → gagal sebelum connect (socket sudah mati),
#    tapi blokir juga import-nya agar error jelas:
for _m in ("requests", "httpx", "aiohttp", "urllib3"):
    sys.modules[_m] = None  # import akan raise ImportError

# 3) Subprocess dibatasi: tidak boleh panggil network CLI (curl/wget/ping/ssh...)
_NET_CMDS = {"curl","wget","ping","ssh","scp","ftp","nc","netcat","telnet","git","pip","npm","apt","pkg"}
_orig_popen = os.popen
def _safe_popen(cmd, *a, **k):
    head = cmd.strip().split()[0] if cmd.strip() else ""
    if os.path.basename(head) in _NET_CMDS:
        raise OSError(f"[SANDBOX] Perintah '{head}' diblokir (network-capable).")
    return _orig_popen(cmd, *a, **k)
os.popen = _safe_popen

# 4) Subprocess module guard
import subprocess as _sp
_orig_run = _sp.run
def _safe_run(cmd, *a, **k):
    c = cmd[0] if isinstance(cmd, (list, tuple)) else str(cmd).strip().split()[0]
    if os.path.basename(str(c)) in _NET_CMDS:
        raise OSError(f"[SANDBOX] Perintah '{c}' diblokir (network-capable).")
    return _orig_run(cmd, *a, **k)
_sp.run = _safe_run

SANDBOX_ACTIVE = True
