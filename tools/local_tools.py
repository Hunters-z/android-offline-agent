import re, os
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


# ================= MEMORY PERSISTEN =================
# Catatan agent tentang user — selalu diinjeksi ke system prompt setiap sesi (ala Hermes MEMORY.md)
_HOME = os.environ.get("LOKA_HOME", os.path.expanduser("~/loka"))
MEM_FILE = os.path.join(_HOME, "memory.md")

def _mem_lines():
    try:
        with open(MEM_FILE) as f:
            return [l.rstrip("\n") for l in f if l.strip()]
    except FileNotFoundError:
        return []

def mem_save(content=None, **kw):
    """Tambah fakta permanen tentang user. Dipanggil agent saat menemukan info penting."""
    if not content:
        # alias arg bebas
        for k, v in kw.items():
            if isinstance(v, str) and v.strip():
                content = v; break
    if not content:
        return {"error": "butuh content"}
    lines = _mem_lines()
    if content.strip() in "\n".join(lines):  # dedupe
        return {"ok": True, "note": "sudah ada"}
    lines.append(content.strip())
    # batas 30 baris — buang tertua
    if len(lines) > 30:
        lines = lines[-30:]
    os.makedirs(_HOME, exist_ok=True)
    with open(MEM_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
    return {"ok": True, "total": len(lines)}

def mem_list(**kw):
    lines = _mem_lines()
    return {"count": len(lines), "items": lines}

def mem_forget(content=None, **kw):
    """Hapus fakta yang memuat substring content."""
    if not content:
        for k, v in kw.items():
            if isinstance(v, str) and v.strip(): content = v; break
    if not content: return {"error": "butuh content"}
    lines = [l for l in _mem_lines() if content.lower() not in l.lower()]
    with open(MEM_FILE, "w") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    return {"ok": True, "sisa": len(lines)}

TOOLS.update({
    "mem_save": mem_save,
    "mem_list": mem_list,
    "mem_forget": mem_forget,
})

# ================= SHELL TERBATAS (project di perangkat) =================
# Folder project: LOKA_HOME/projects/<nama>. Agent tidak bisa keluar dari situ.
# Perintah di-allowlist ketat; eksekusi WAJIB lewat approval sheet (bukan SAFE_TOOLS).
PROJECTS_ROOT = os.path.join(SAFE_ROOT, "projects")
SHELL_BINARIES = {
    "git":   ["git"],
    "node":  ["node"],
    "npm":   ["npm", "npx"],
    "python":["python3"],
    "ls":    ["ls", "cat", "head", "tail", "wc", "grep", "find", "du"],
    "text":  ["sed", "awk", "sort", "uniq", "cut", "tr", "diff", "touch", "mkdir", "cp", "mv"],
}
SHELL_MAX_OUT = 4000

def _project_dir(name=None):
    os.makedirs(PROJECTS_ROOT, exist_ok=True)
    if not name:
        # kalau hanya ada satu project, pakai itu
        subs = [d for d in os.listdir(PROJECTS_ROOT) if os.path.isdir(os.path.join(PROJECTS_ROOT, d))]
        if len(subs) == 1: name = subs[0]
        else: return None, subs
    pd = os.path.realpath(os.path.join(PROJECTS_ROOT, name))
    if not pd.startswith(os.path.realpath(PROJECTS_ROOT)):
        raise ValueError("Nama project tidak valid")
    return pd, None

def shell(command=None, project=None, **kw):
    """Jalankan perintah terbatas di folder project di perangkat.
    Hanya binary allowlist; wajib approval user (tool berisiko)."""
    if not command or not isinstance(command, str):
        return {"error": "butuh command"}
    import shlex
    try:
        parts = shlex.split(command)
    except ValueError as e:
        return {"error": "command tidak bisa diparse: %s" % e}
    if not parts:
        return {"error": "command kosong"}
    # pipe/redirect/metachar dilarang — satu perintah sederhana saja
    if any(ch in command for ch in "|;&`$><\n"):
        return {"error": "hanya perintah tunggal tanpa |;&`$>< (pecah jadi beberapa panggilan shell)"}
    bin0 = parts[0]
    allowed = any(bin0 in alts or bin0 == a for alts in SHELL_BINARIES.values() for a in alts)
    if not allowed:
        return {"error": "perintah '%s' tidak di-allowlist. Boleh: git, node, npm, npx, python3, ls, cat, head, tail, grep, find, sed, awk, mkdir, cp, mv, touch, diff, wc, du" % bin0}
    # hardening: larang path absolut & traversal keluar project
    for tok in parts[1:]:
        if tok.startswith("/"):
            return {"error": "path absolut tidak diizinkan — pakai path relatif dalam project"}
    pd, subs = _project_dir(project)
    if pd is None:
        return {"error": "pilih project. Project tersedia: %s (buat via file_write di projects/<nama>/...)" % ", ".join(subs) if subs else "belum ada project — buat via file_write di projects/<nama>/..."}
    if not os.path.isdir(pd):
        return {"error": "project tidak ditemukan: %s" % pd}
    for tok in parts[1:]:
        if "/" in tok:
            rp = os.path.realpath(os.path.join(pd, tok))
            if not rp.startswith(pd + os.sep) and rp != pd:
                return {"error": "path keluar dari folder project: %s" % tok}
    try:
        import subprocess as _sp
        r = _sp.run(parts, cwd=pd, capture_output=True, text=True, timeout=30,
                    env={**os.environ, "HOME": pd, "PATH": os.environ.get("PATH", "/usr/bin:/bin")})
        out = (r.stdout or "")[:SHELL_MAX_OUT]
        err = (r.stderr or "")[:1500]
        return {"ok": True, "exit": r.returncode, "cwd": os.path.basename(pd),
                "stdout": out, "stderr": err, "terpotong": len(r.stdout or "") > SHELL_MAX_OUT}
    except _sp.TimeoutExpired:
        return {"error": "timeout 30 detik"}
    except FileNotFoundError:
        return {"error": "binary tidak ada di perangkat: %s" % bin0}

TOOLS.update({
    "shell": shell,
})
