"""Loka Engine — server lokal (127.0.0.1 saja, TIDAK mengekspos network keluar).
Melayani UI Muse-style + API chat. Jalankan di dalam jail proot."""
import json, os, sys, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler, BaseHTTPRequestHandler

HOME = os.environ.get("LOKA_HOME", os.path.expanduser("~/loka"))
SETTINGS_FILE = os.path.join(HOME, "ai_settings.json")
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.core import parse_tool_call, reload_system_prompt
from tools.local_tools import TOOLS

# ============ APPROVAL SYSTEM ============
SAFE_TOOLS = {"calc","now","battery","mem_list","note_list","file_list"}  # auto-approve
APPROVAL_FILE = os.path.join(HOME, "approval_policy.json")   # {"always": ["file_write",...]}
PENDING_DIR = os.path.join(HOME, "pending")                  # 1 file per request

_SESSION_OK = set()          # tool disetujui utk sesi server (sampai restart)
_CHAT_OK = {}                # chat_id -> set(tool) utk percakapan ini

def _load_policy():
    try: return json.load(open(APPROVAL_FILE))
    except Exception: return {"always": []}

def _needs_approval(name, chat_id=None):
    if name in SAFE_TOOLS: return False
    if name in _SESSION_OK: return False
    if chat_id and name in _CHAT_OK.get(chat_id, set()): return False
    return name not in _load_policy().get("always", [])

def _request_approval(name, args, chat_id=None):
    import uuid, time as _t
    os.makedirs(PENDING_DIR, exist_ok=True)
    rid = uuid.uuid4().hex[:12]
    req = {"id": rid, "tool": name, "args": args, "status": "pending", "ts": _t.time(),
           "chat_id": chat_id or ""}
    json.dump(req, open(os.path.join(PENDING_DIR, rid + ".json"), "w"))
    for _ in range(120):
        _t.sleep(1)
        try: cur = json.load(open(os.path.join(PENDING_DIR, rid + ".json")))
        except Exception: return {"status":"error"}
        st = cur.get("status")
        if st != "pending":
            try: os.remove(os.path.join(PENDING_DIR, rid + ".json"))
            except Exception: pass
            # terapkan scope
            if st == "approved_chat" and (chat_id or cur.get("chat_id")):
                cid = chat_id or cur.get("chat_id")
                _CHAT_OK.setdefault(cid, set()).add(name)
            elif st == "approved_always":
                pol = _load_policy()
                if name not in pol.get("always", []):
                    pol.setdefault("always", []).append(name)
                    json.dump(pol, open(APPROVAL_FILE, "w"))
            return cur
    return {"status":"timeout"}

def load_settings():
    try: return json.load(open(SETTINGS_FILE))
    except Exception: return {"mode":"local","provider":"openai","base_url":"https://api.openai.com/v1","api_key":"","model":"gpt-4o-mini"}

def save_settings(st):
    json.dump(st, open(SETTINGS_FILE,"w"))
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "android", "app")

# Sandbox tetap aktif (guard berjalan saat import)
from agent import sandbox  # noqa

from tools.model_manager import model_path, list_models, set_active, get_active
_llm = None; _lock = threading.Lock(); _loaded_key = None

def llm():
    global _llm, _loaded_key
    key = get_active() or "tiny"
    if _llm is None or _loaded_key != key:
        from llama_cpp import Llama
        _llm = Llama(model_path=model_path(key), n_ctx=2048, verbose=False, n_threads=max(2, os.cpu_count()-1))
        _loaded_key = key
    return _llm


# ============ SKILL INSTALL DARI GITHUB ============
def _install_skill_from_github(url):
    """Install skill dari URL GitHub (folder berisi SKILL.md atau file .md langsung).
       Format: github.com/user/repo/tree/branch/path  |  .../blob/.../SKILL.md  |  raw URL"""
    import urllib.request as _ur
    url = url.replace("https://github.com/", "").replace("http://github.com/", "")
    url = url.replace("https://raw.githubusercontent.com/", "")
    # raw URL langsung
    parts_all = url.strip("/").split("/")
    if len(parts_all) >= 4 and parts_all[2] == "refs":  # raw/refs/heads/...
        parts = parts_all; branch = parts[3]; path = "/".join(parts[4:])
    else:
        parts = parts_all
    # github.com/user/repo/tree/branch/path
    if len(parts) >= 5 and parts[2] in ("tree","blob"):
        user, repo, kind, branch = parts[0], parts[1], parts[2], parts[3]
        path = "/".join(parts[4:])
    elif len(parts) >= 4 and parts[2] == "raw":  # raw.githubusercontent style user/repo/branch/path? jarang
        user, repo, branch = parts[0], parts[1], parts[2]
        path = "/".join(parts[3:])
    elif len(parts) >= 2:
        user, repo = parts[0], parts[1]
        branch = "main"
        path = "/".join(parts[2:]) if len(parts) > 2 else ""
    else:
        raise ValueError("URL tidak dikenali — pakai URL folder/file di github.com")
    base_raw = "https://raw.githubusercontent.com/%s/%s/%s" % (user, repo, branch)

    def fetch(p):
        req = _ur.Request(base_raw + "/" + p, headers={"User-Agent":"loka-agent"})
        with _ur.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", "replace")

    # izinkan host github di sandbox
    try:
        import agent.sandbox as _sb; _sb.allow_host("raw.githubusercontent.com")
    except Exception: pass

    name = path.rstrip("/").split("/")[-1] if path else repo
    files = {}
    # kasus 1: path menuju file .md langsung
    if path.endswith(".md"):
        files[name[:-3] if name.endswith(".md") else name] = fetch(path)
    else:
        # kasus 2: folder — coba SKILL.md dulu, lalu ambil .md lain via API listing
        try:
            files["SKILL"] = fetch(path.rstrip("/") + "/SKILL.md")
            name = path.rstrip("/").split("/")[-1]
        except Exception:
            # fallback: coba README.md
            files[name or "skill"] = fetch(path.rstrip("/") + "/README.md")
        # file .md tambahan dalam folder (via GitHub API) — hanya utk subfolder, bukan root repo
        if path:
          try:
            api = "https://api.github.com/repos/%s/%s/contents/%s?ref=%s" % (user, repo, path, branch)
            try:
                import agent.sandbox as _sb; _sb.allow_host("api.github.com")
            except Exception: pass
            req = _ur.Request(api, headers={"User-Agent":"loka-agent"})
            with _ur.urlopen(req, timeout=20) as r:
                import json as _j
                listing = _j.loads(r.read())
            for it in listing:
                if it.get("type")=="file" and it.get("name","").endswith(".md") and it["name"]!="SKILL.md" and it["name"]!="README.md" and len(files)<8:
                    try: files[it["name"][:-3]] = fetch(path.rstrip("/") + "/" + it["name"])
                    except Exception: pass
          except Exception: pass
    if not files:
        raise ValueError("tidak menemukan SKILL.md / file markdown di URL itu")
    sk_dir = os.path.join(HOME, "skills")
    os.makedirs(sk_dir, exist_ok=True)
    # nama folder skill = nama utama
    main = "SKILL" if "SKILL" in files else list(files)[0]
    installed = []
    for fn, content in files.items():
        fname = ("%s__%s" % (name, fn)) if len(files) > 1 else name
        with open(os.path.join(sk_dir, fname + ".md"), "w") as f:
            f.write(content)
        installed.append(fname)
    return {"ok": True, "installed": installed, "count": len(installed)}

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw): super().__init__(*a, directory=APP_DIR, **kw)
    def log_message(self, *a): pass
    def _api_chat(self, st, messages):
        """Satu panggilan ke LLM via API (OpenAI-compatible)."""
        import urllib.request
        req = urllib.request.Request(
            st["base_url"].rstrip("/") + "/chat/completions",
            data=json.dumps({"model": st.get("model","gpt-4o-mini"), "messages": messages, "max_tokens": 1000}).encode(),
            headers={"Content-Type":"application/json","Authorization":"Bearer "+st["api_key"]})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())

    def _agent_loop_api(self, st, msgs):
        """Agent loop: model via API hanya OTAK; tangan = tools lokal di device.
           Maks 6 iterasi. Tool hasil di-inject, model putuskan langkah berikut."""
        history = list(msgs)
        for _ in range(6):
            out = self._api_chat(st, [{"role":"system","content":reload_system_prompt(history[-1]["content"] if history else "")}] + history)
            text = (out["choices"][0]["message"].get("content") or "").strip()
            call = parse_tool_call(text)
            print("[loop] text=%r call=%r" % (text[:120], call))
            if not call or not call.get("tool"):
                return out  # jawaban final
            name, args = call.get("tool"), call.get("args", {})
            chat_id = None
            for _m in msgs:
                if _m.get("role") == "user" and not _m.get("content","").startswith("[HASIL TOOL]"):
                    chat_id = str(hash(_m["content"]) % 10**8); break
            if _needs_approval(name, chat_id):
                dec = _request_approval(name, args, chat_id)
                if not str(dec.get("status","")).startswith("approved"):
                    result = {"error": "[DITOLAK USER] aksi %s tidak diizinkan (%s)" % (name, dec.get("status"))}
                    history.append({"role":"assistant","content":text})
                    history.append({"role":"user","content":"[HASIL TOOL] " + json.dumps(result, ensure_ascii=False)})
                    continue
            try:
                if name not in TOOLS:
                    result = {"error": "tool '%s' tidak ada" % name}
                else:
                    result = TOOLS[name](**args) if isinstance(args, dict) else TOOLS[name](args)
            except Exception as ex:
                result = {"error": str(ex)}
            history.append({"role":"assistant","content":text})
            history.append({"role":"user","content":"[HASIL TOOL] " + json.dumps(result, ensure_ascii=False)})
        return out  # habis iterasi — kembalikan apa adanya


    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path == "/api/cron":
            import glob as _g
            jobs = []
            for f in _g.glob(os.path.join(CRON_DIR, "*.json")):
                try: jobs.append(json.load(open(f)))
                except Exception: pass
            return self._json({"items": jobs})
        if self.path == "/api/cron/add":
            import uuid as _u
            os.makedirs(CRON_DIR, exist_ok=True)
            job = {"id": _u.uuid4().hex[:10], "name": body.get("name","rutinitas"),
                   "task": body.get("task",""), "interval_minutes": int(body.get("interval_minutes",60)),
                   "last_run": 0, "paused": False}
            json.dump(job, open(os.path.join(CRON_DIR, job["id"] + ".json"), "w"))
            return self._json({"ok": True, "id": job["id"]})
        if self.path.startswith("/api/cron/del/"):
            rid = self.path.rsplit("/",1)[-1]
            try: os.remove(os.path.join(CRON_DIR, rid + ".json"))
            except Exception: pass
            return self._json({"ok": True})
        if self.path == "/api/feed":
            feed = os.path.join(HOME, "feed.jsonl")
            items = []
            try:
                with open(feed) as f:
                    items = [json.loads(l) for l in f if l.strip()]
            except FileNotFoundError: pass
            return self._json({"items": items[-20:][::-1]})
        if self.path == "/api/skills":
            import glob as _g
            sk_dir = os.path.join(HOME, "skills")
            os.makedirs(sk_dir, exist_ok=True)
            items = []
            for f in sorted(_g.glob(os.path.join(sk_dir, "*.md"))):
                try:
                    c = open(f).read().strip()
                    desc = c.split("\n")[0][:100]
                    if desc == "---":  # frontmatter → ambil description:
                        import re as _re
                        m = _re.search(r"^description:\s*(.+)$", c, _re.M)
                        if m: desc = m.group(1).strip()[:100]
                    items.append({"name": os.path.basename(f)[:-3], "desc": desc, "size": len(c)})
                except Exception: pass
            return self._json({"items": items})
        if self.path == "/api/pending":
            import glob
            reqs = []
            for f in glob.glob(os.path.join(PENDING_DIR, "*.json")):
                try: reqs.append(json.load(open(f)))
                except Exception: pass
            return self._json({"items": reqs})
        if self.path.startswith("/api/approve/"):
            rid = self.path.rsplit("/",1)[-1].split("?")[0]
            fp = os.path.join(PENDING_DIR, rid + ".json")
            try: cur = json.load(open(fp))
            except Exception: return self._json({"error":"tidak ada"},404)
            level = body.get("level","once")   # once | chat | always | deny
            cur["status"] = {"once":"approved","chat":"approved_chat","always":"approved_always","deny":"denied"}.get(level,"denied")
            json.dump(cur, open(fp,"w"))
            return self._json({"ok":True})
        if self.path == "/api/settings":
            st = load_settings()
            safe = dict(st); safe["api_key"] = (st.get("api_key","")[:4] + "…" ) if st.get("api_key") else ""
            return self._json(safe)
        if self.path == "/api/models":
            return self._json({m["key"]: {"downloaded": m["downloaded"], "active": m["active"]} for m in list_models()})
        return super().do_GET()
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/api/model":
            try:
                r = set_active(body.get("model","tiny")); return self._json({"ok": True, **r})
            except ValueError as e: return self._json({"ok": False, "error": str(e)}, 400)
        if self.path == "/api/cron":
            import glob as _g
            jobs = []
            for f in _g.glob(os.path.join(CRON_DIR, "*.json")):
                try: jobs.append(json.load(open(f)))
                except Exception: pass
            return self._json({"items": jobs})
        if self.path == "/api/cron/add":
            import uuid as _u
            os.makedirs(CRON_DIR, exist_ok=True)
            job = {"id": _u.uuid4().hex[:10], "name": body.get("name","rutinitas"),
                   "task": body.get("task",""), "interval_minutes": int(body.get("interval_minutes",60)),
                   "last_run": 0, "paused": False}
            json.dump(job, open(os.path.join(CRON_DIR, job["id"] + ".json"), "w"))
            return self._json({"ok": True, "id": job["id"]})
        if self.path.startswith("/api/cron/del/"):
            rid = self.path.rsplit("/",1)[-1]
            try: os.remove(os.path.join(CRON_DIR, rid + ".json"))
            except Exception: pass
            return self._json({"ok": True})
        if self.path == "/api/feed":
            feed = os.path.join(HOME, "feed.jsonl")
            items = []
            try:
                with open(feed) as f:
                    items = [json.loads(l) for l in f if l.strip()]
            except FileNotFoundError: pass
            return self._json({"items": items[-20:][::-1]})
        if self.path.startswith("/api/skills/del/"):
            name = self.path.rsplit("/",1)[-1]
            try: os.remove(os.path.join(HOME, "skills", name + ".md"))
            except Exception: pass
            return self._json({"ok": True})
        if self.path == "/api/skills/install":
            url = (body.get("url","") or "").strip()
            if not url: return self._json({"error":"butuh url"}, 400)
            try:
                res = _install_skill_from_github(url)
                return self._json(res)
            except Exception as e:
                return self._json({"error": str(e)}, 400)
        if self.path == "/api/pending":
            import glob
            reqs = []
            for f in glob.glob(os.path.join(PENDING_DIR, "*.json")):
                try: reqs.append(json.load(open(f)))
                except Exception: pass
            return self._json({"items": reqs})
        if self.path.startswith("/api/approve/"):
            rid = self.path.rsplit("/",1)[-1].split("?")[0]
            fp = os.path.join(PENDING_DIR, rid + ".json")
            try: cur = json.load(open(fp))
            except Exception: return self._json({"error":"tidak ada"},404)
            level = body.get("level","once")   # once | chat | always | deny
            cur["status"] = {"once":"approved","chat":"approved_chat","always":"approved_always","deny":"denied"}.get(level,"denied")
            json.dump(cur, open(fp,"w"))
            return self._json({"ok":True})
        if self.path == "/api/settings":
            # simpan konfigurasi provider
            allowed = {k: body.get(k) for k in ("mode","provider","base_url","api_key","model") if k in body}
            st = load_settings(); st.update(allowed); save_settings(st)
            return self._json({"ok": True, "mode": st["mode"]})
        if self.path == "/v1/chat/completions":
            st = load_settings()
            from agent import sandbox as _sb
            if st.get("mode") in ("cloud","hybrid") and st.get("base_url"):
                try:
                    from urllib.parse import urlparse
                    _sb.allow_host(urlparse(st["base_url"]).netloc.split(":")[0])
                except Exception: pass
            msgs = body.get("messages", [])
            # MODE CLOUD/HYBRID: AGENT LOOP — model via API memutuskan,
            # AGENT (device ini) mengeksekusi tools lokal & berulang sampai jawaban final.
            if st.get("mode") in ("cloud","hybrid") and st.get("api_key") and st.get("base_url"):
                try:
                    return self._json(self._agent_loop_api(st, msgs))
                except Exception as e:
                    if st.get("mode") == "hybrid":
                        pass  # fallback ke lokal di bawah
                    else:
                        return self._json({"error": "API gagal: %s" % e}, 502)
            # MODE LOKAL
            try:
                with _lock:
                    out = llm().create_chat_completion(messages=msgs, max_tokens=500, temperature=0.4)
                return self._json(out)
            except Exception as e:
                return self._json({"error": str(e)}, 500)
        return self._json({"error": "not found"}, 404)

# ============ CRON / ROUTINES ============
# Rutinitas berjalan sendiri walau UI ditutup — agent loop penuh (tools lokal + otak).
import threading as _threading
import time as _time
import glob as _glob
CRON_DIR = os.path.join(HOME, "cron")

def _cron_run_job(job):
    """Eksekusi 1 job: buat pesan tugas → agent loop (otak sesuai mode aktif)."""
    task = job.get("task","")
    msgs = [{"role":"user","content":"[ROUTINE] " + task}]
    try:
        st = load_settings()
        if st.get("mode") in ("cloud","hybrid") and st.get("api_key"):
            out = _agent_loop_api(None, st, msgs) if False else None
        # gunakan fungsi loop milik handler lewat helper global
        out = agent_loop_run(msgs)
        result = out["choices"][0]["message"]["content"] if out else "gagal"
    except Exception as e:
        result = "error: %s" % e
    # simpan hasil ke feed
    feed = os.path.join(HOME, "feed.jsonl")
    with open(feed, "a") as f:
        f.write(json.dumps({"ts": _time.time(), "task": task, "result": result, "source": job.get("name","routine")}, ensure_ascii=False) + "\n")
    return result

def agent_loop_run(msgs):
    """Agent loop generik module-level: otak sesuai mode (API/lokal), tools lokal, approval."""
    st = load_settings()
    use_api = st.get("mode") in ("cloud","hybrid") and st.get("api_key") and st.get("base_url")
    history = [m for m in msgs if m.get("role") != "system"]  # hardening: system eksternal dibuang — hanya system prompt Loka
    out = None
    for _ in range(6):
        sys_msg = {"role":"system","content":reload_system_prompt(history[-1]["content"] if history else "")}
        if use_api:
            import urllib.request
            from urllib.parse import urlparse
            try:
                import agent.sandbox as _sb
                _sb.allow_host(urlparse(st["base_url"]).netloc.split(":")[0])
            except Exception: pass
            req = urllib.request.Request(
                st["base_url"].rstrip("/") + "/chat/completions",
                data=json.dumps({"model": st.get("model","gpt-4o-mini"), "messages":[sys_msg]+history, "max_tokens": 1000}).encode(),
                headers={"Content-Type":"application/json","Authorization":"Bearer "+st["api_key"]})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    out = json.loads(r.read())
            except Exception as e:
                if st.get("mode") == "hybrid": use_api = False; continue
                return {"choices":[{"message":{"content":"API gagal: %s" % e}}]}
        else:
            try:
                with _lock:
                    out = llm().create_chat_completion(messages=[sys_msg]+history, max_tokens=500, temperature=0.4)
            except Exception as e:
                return {"choices":[{"message":{"content":"error: %s" % e}}]}
        text = (out["choices"][0]["message"].get("content") or "").strip()
        call = parse_tool_call(text)
        if not call or not call.get("tool"):
            return out
        name, args = call.get("tool"), call.get("args", {})
        if _needs_approval(name):
            dec = _request_approval(name, args)
            if not str(dec.get("status","")).startswith("approved"):
                result = {"error": "[DITOLAK USER] %s (%s)" % (name, dec.get("status"))}
            else:
                result = _run_tool(name, args)
        else:
            result = _run_tool(name, args)
        history.append({"role":"assistant","content":text})
        history.append({"role":"user","content":"[HASIL TOOL] " + json.dumps(result, ensure_ascii=False)})
    return out

def _run_tool(name, args):
    try:
        if name not in TOOLS:
            return {"error": "tool '%s' tidak ada" % name}
        return TOOLS[name](**args) if isinstance(args, dict) else TOOLS[name](args)
    except Exception as ex:
        return {"error": str(ex)}

def _cron_scheduler():
    os.makedirs(CRON_DIR, exist_ok=True)
    while True:
        now = _time.time()
        try:
            for fp in _glob.glob(os.path.join(CRON_DIR, "*.json")):
                try: job = json.load(open(fp))
                except Exception: continue
                if job.get("paused"): continue
                interval = int(job.get("interval_minutes", 60)) * 60
                if now - job.get("last_run", 0) >= interval:
                    job["last_run"] = now
                    json.dump(job, open(fp, "w"))
                    _threading.Thread(target=_cron_run_job, args=(job,), daemon=True).start()
        except Exception as e:
            print("[cron] error:", e)
        _time.sleep(60)

_threading.Thread(target=_cron_scheduler, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("LOKA_PORT", "8088"))
    print(f"[loka] engine UI: http://127.0.0.1:{port}  (buka di browser HP)")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()

