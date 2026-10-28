"""
Tool lokal agent — semua berjalan offline di dalam container.
Agent hanya boleh memanggil tool di daftar ini (whitelist).
"""
import json, os, time, math, subprocess

SAFE_ROOT = os.environ.get("LOKA_HOME", os.path.expanduser("~/loka"))
os.makedirs(SAFE_ROOT, exist_ok=True)

def _safe_path(rel):
    p = os.path.realpath(os.path.join(SAFE_ROOT, rel.lstrip("/")))
    if not p.startswith(os.path.realpath(SAFE_ROOT)):
        raise ValueError("Akses di luar folder sandbox tidak diizinkan")
    return p

# --- kalkulator aman (tanpa eval bebas) ---
def calc(expression=None, percent=None, value=None, **_):
    if expression is None and percent is not None and value is not None:
        expression = f"({percent})/100*({value})"
    if expression is None:
        return {"error": "butuh expression, atau percent+value"}
    allowed = {n: getattr(math, n) for n in
        ("sqrt","sin","cos","tan","log","log10","exp","floor","ceil","fabs","pow")}
    allowed.update({"pi": math.pi, "e": math.e, "abs": abs, "round": round, "min": min, "max": max})
    try:
        return {"result": eval(expression, {"__builtins__": {}}, allowed)}
    except Exception as e:
        return {"error": str(e)}

# --- catatan (notes) ---
def note_save(title, body):
    p = _safe_path("notes")
    os.makedirs(p, exist_ok=True)
    fn = os.path.join(p, f"{int(time.time())}_{title.replace(' ','_')[:40]}.md")
    open(fn, "w").write(f"# {title}\n\n{body}\n")
    return {"saved": fn}

def note_list():
    p = _safe_path("notes")
    if not os.path.isdir(p): return {"notes": []}
    return {"notes": sorted(os.listdir(p), reverse=True)}

def note_read(name):
    return {"content": open(_safe_path(f"notes/{name}")).read()}

# --- baca/tulis file di sandbox ---
def file_write(name, content):
    p = _safe_path(name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(content)
    return {"written": p}

def file_read(name):
    return {"content": open(_safe_path(name)).read()}

def file_list(name=""):
    p = _safe_path(name)
    return {"files": sorted(os.listdir(p)) if os.path.isdir(p) else []}

# --- waktu & sistem ---
def now(_=None):
    return {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "uptime_s": int(time.monotonic())}

def battery(_=None):
    # Termux: termux-battery-status (API Termux, tanpa network)
    try:
        out = subprocess.check_output(["termux-battery-status"], timeout=5)
        d = json.loads(out)
        return {"percent": d.get("percentage"), "status": d.get("status")}
    except Exception:
        return {"percent": None, "status": "termux-api tidak tersedia"}

# daftar tool yang boleh dipakai LLM (whitelist)
TOOLS = {
    "calc": calc, "note_save": note_save, "note_list": note_list,
    "note_read": note_read, "file_write": file_write, "file_read": file_read,
    "file_list": file_list, "now": now, "battery": battery,
}
