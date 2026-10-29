"""Loka Engine — server lokal (127.0.0.1 saja, TIDAK mengekspos network keluar).
Melayani UI Muse-style + API chat. Jalankan di dalam jail proot."""
import json, os, sys, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from http.server import HTTPServer, SimpleHTTPRequestHandler, BaseHTTPRequestHandler

HOME = os.environ.get("LOKA_HOME", os.path.expanduser("~/loka"))
SETTINGS_FILE = os.path.join(HOME, "ai_settings.json")
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.core import parse_tool_call, reload_system_prompt
from tools.local_tools import TOOLS

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

if __name__ == "__main__":
    port = int(os.environ.get("LOKA_PORT", "8088"))
    print(f"[loka] engine UI: http://127.0.0.1:{port}  (buka di browser HP)")
    HTTPServer(("127.0.0.1", port), H).serve_forever()
