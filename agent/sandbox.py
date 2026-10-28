"""
Sandbox ketat: blokir SEMUA akses network di level interpreter.
Agent tidak bisa keluar ke internet — bahkan jika prompt-nya mencoba.
Import modul ini SEBELUM modul lain apa pun.
"""
import socket, builtins, os, sys

_blocked_msg = "[SANDBOX] Akses network diblokir. Agent ini offline-total."

def _blocked(*a, **k):
    raise OSError(_blocked_msg)

# 1) Socket: netralisir total
socket.socket = _blocked
socket.create_connection = _blocked
socket.getaddrinfo = _blocked
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
