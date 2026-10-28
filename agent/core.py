"""
Loka — agent AI offline untuk Android.
Engine: llama-cpp-python (GGUF lokal). Tools: whitelist lokal. Network: diblokir total.
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import agent.sandbox  # WAJIB paling awal — blokir network
from tools.local_tools import TOOLS

MODEL = os.environ.get("LOKA_MODEL", os.path.expanduser("~/loka/models/model-q4.gguf"))
CTX = int(os.environ.get("LOKA_CTX", "2048"))

SYSTEM = (
    "Kamu adalah Loka, asisten AI offline berbahasa Indonesia yang berjalan di ponsel pengguna. "
    "Jawab ringkas dan langsung. Kamu punya tool lokal: calc, note_save, note_list, note_read, "
    "file_write, file_read, file_list, now, battery. "
    "Jika perlu tool, jawab HANYA satu baris JSON: {\"tool\": \"nama\", \"args\": {...}} "
    "tanpa teks lain. Setelah hasil tool diberikan, jawab pertanyaan user dengan bahasa manusia. "
    "Kamu TIDAK punya akses internet dan tidak boleh mengaku bisa."
)

_llm = None
def llm():
    global _llm
    if _llm is None:
        from llama_cpp import Llama
        print(f"[loka] memuat model: {MODEL}")
        _llm = Llama(model_path=MODEL, n_ctx=CTX, n_threads=os.cpu_count(), verbose=False)
    return _llm

TOOL_RE = re.compile(r'\{\s*\"tool\".*?\}', re.S)

def step(history):
    """Satu putaran: generate; jika minta tool → jalankan tool lokal → inject hasil."""
    out = llm().create_chat_completion(
        messages=[{"role":"system","content":SYSTEM}] + history,
        max_tokens=300, temperature=0.4,
    )
    text = out["choices"][0]["message"]["content"].strip()
    m = TOOL_RE.search(text)
    if m:
        try:
            call = json.loads(m.group(0))
            name, args = call.get("tool"), call.get("args", {})
            if name not in TOOLS:
                result = {"error": f"tool '{name}' tidak ada"}
            else:
                result = TOOLS[name](**args) if isinstance(args, dict) else TOOLS[name](args)
            history.append({"role":"assistant","content":text})
            history.append({"role":"user","content":"[HASIL TOOL] " + json.dumps(result, ensure_ascii=False)})
            return step(history)  # lanjut jawab dengan hasil tool
        except Exception as e:
            return f"[tool error] {e}"
    return text

def chat():
    print("Loka offline-agent — sandbox aktif, tanpa internet. (ketik /exit untuk keluar)")
    history = []
    while True:
        try:
            q = input("\nKamu ▸ ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q: continue
        if q in ("/exit","/quit"): break
        if q == "/tools": print(", ".join(TOOLS)); continue
        history.append({"role":"user","content":q})
        try:
            a = step(history)
        except Exception as e:
            a = f"[error] {e}"
        history.append({"role":"assistant","content":a})
        print(f"\nLoka ▸ {a}")
        if len(history) > 20: history = history[-16:]  # jaga memori kecil

if __name__ == "__main__":
    chat()
