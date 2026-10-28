"""Loka Engine — server lokal (127.0.0.1 saja, TIDAK mengekspos network keluar).
Melayani UI Muse-style + API chat. Jalankan di dalam jail proot."""
import json, os, sys, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from http.server import HTTPServer, SimpleHTTPRequestHandler, BaseHTTPRequestHandler

HOME = os.environ.get("LOKA_HOME", os.path.expanduser("~/loka"))
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
    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path == "/api/models":
            return self._json({m["key"]: {"downloaded": m["downloaded"], "active": m["active"]} for m in list_models()})
        return super().do_GET()
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/api/model":
            try:
                r = set_active(body.get("model","tiny")); return self._json({"ok": True, **r})
            except ValueError as e: return self._json({"ok": False, "error": str(e)}, 400)
        if self.path == "/v1/chat/completions":
            msgs = body.get("messages", [])
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
