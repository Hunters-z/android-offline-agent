import re
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
def calc(expression=None, percent=None, value=None, total=None, **kw):
    value = value or total
    # model kecil kirim nama arg bebas: persen/total/dll — deteksi otomatis
    if percent is None:
        for k, v in kw.items():
            if k.lower().startswith("persen") or k.lower().startswith("percent"):
                percent = v
    if value is None:
        for k, v in kw.items():
            if k.lower() in ("value", "total", "angka", "dari", "number", "jumlah") or str(v).replace('.','',1).isdigit():
                value = v; break
    if expression is None and percent is not None and value is not None:
        expression = f"({percent})/100*({value})"
    if expression is None and value is not None:
        expression = str(value)
    if expression is None:
        return {"error": "butuh expression, atau percent+value"}
    # pola bahasa Indonesia: "25% dari 1.200.000", "25 persen dari 1.2 juta", "diskon 20% dari 150000"
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:%|persen|percent)\s*(?:dari|of|diskon\s*(?:dari)?)\s*([\d.,]+(?:\s*(?:juta|ribu|miliar))?)", str(expression), re.I)
    if m:
        pct, val = m.group(1), m.group(2)
        mult = 1
        vl = val.lower()
        if "juta" in vl: mult, val = 1_000_000, re.sub(r"\s*juta", "", vl)
        elif "miliar" in vl: mult, val = 1_000_000_000, re.sub(r"\s*miliar", "", vl)
        elif "ribu" in vl: mult, val = 1_000, re.sub(r"\s*ribu", "", vl)
        def _num(t):
            t = t.strip()
            if "," in t and "." in t: return float(t.replace(".", "").replace(",", "."))
            if "," in t: return float(t.replace(",", "."))
            import re as _re
            if _re.fullmatch(r"\d{1,3}(\.\d{3})+", t): return float(t.replace(".", ""))
            return float(t)
        val = _num(val)
        expression = f"({pct.replace(',', '.')})/100*({val}*{mult})"

    allowed = {n: getattr(math, n) for n in
        ("sqrt","sin","cos","tan","log","log10","exp","floor","ceil","fabs","pow")}
    allowed.update({"pi": math.pi, "e": math.e, "abs": abs, "round": round, "min": min, "max": max})
    try:
        return {"result": eval(expression, {"__builtins__": {}}, allowed)}
    except Exception as e:
        return {"error": str(e)}

# --- catatan (notes) ---
def note_save(title=None, body=None, judul=None, isi=None, content=None, **_):
    title = title or judul
    body = body or isi or content
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
