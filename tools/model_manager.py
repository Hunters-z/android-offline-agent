"""Kelola model GGUF: katalog, unduh, pilih aktif. (Network hanya saat unduh —
proses unduh dijalankan dari Termux di LUAR sandbox agent.)"""
import json, os

MODELS_FILE = os.path.join(os.environ.get("LOKA_HOME", os.path.expanduser("~/loka")), "models.json")
ACTIVE_FILE = os.path.join(os.environ.get("LOKA_HOME", os.path.expanduser("~/loka")), "active_model.txt")

CATALOG = {
  "tiny": { "name":"Qwen2.5-0.5B Q4_K_M", "size_mb": 491, "ram": "3 GB+",
    "file":"model-tiny.gguf",
    "url":"https://modelscope.cn/models/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/master/qwen2.5-0.5b-instruct-q4_k_m.gguf" },
  "small": { "name":"Qwen2.5-1.5B Q4_K_M", "size_mb": 986, "ram": "4 GB+",
    "file":"model-small.gguf",
    "url":"https://modelscope.cn/models/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/master/qwen2.5-1.5b-instruct-q4_k_m.gguf" },
  "medium": { "name":"Qwen2.5-3B Q4_K_M", "size_mb": 1985, "ram": "6 GB+",
    "file":"model-medium.gguf",
    "url":"https://modelscope.cn/models/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/master/qwen2.5-3b-instruct-q4_k_m.gguf" },
  "smart": { "name":"Qwen2.5-7B Q4_K_M", "size_mb": 4677, "ram": "8 GB+",
    "file":"model-smart.gguf",
    "url":"https://modelscope.cn/models/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/master/qwen2.5-7b-instruct-q4_k_m.gguf" },
}

def _load_saved():
    if os.path.exists(MODELS_FILE):
        return json.load(open(MODELS_FILE))
    return {}

def list_models():
    saved = _load_saved()
    out = []
    for key, m in CATALOG.items():
        path = os.path.join(os.path.dirname(MODELS_FILE), m["file"])
        have = os.path.exists(path) and os.path.getsize(path) > 10_000_000
        out.append({"key":key, "name":m["name"], "size_mb":m["size_mb"], "ram":m["ram"],
                    "downloaded":have, "active": get_active()==key})
    return out

def get_active():
    if os.path.exists(ACTIVE_FILE):
        return open(ACTIVE_FILE).read().strip()
    return "tiny" if os.path.exists(os.path.join(os.path.dirname(MODELS_FILE), "model-tiny.gguf")) else None

def set_active(key):
    if key not in CATALOG: raise ValueError(f"model '{key}' tidak ada di katalog")
    open(ACTIVE_FILE,"w").write(key)
    return {"active": key, "name": CATALOG[key]["name"]}

def model_path(key=None):
    key = key or get_active() or "tiny"
    return os.path.join(os.path.dirname(MODELS_FILE), CATALOG[key]["file"])

def download_command(key):
    """Cetak perintah unduh — dijalankan di Termux (luar sandbox), butuh internet."""
    m = CATALOG[key]
    return (f"curl -L -H 'User-Agent: Mozilla/5.0' -C - -o $LOKA/models/{m['file']} '{m['url']}'")
