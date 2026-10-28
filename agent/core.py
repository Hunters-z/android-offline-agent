"""
Loka — agent AI offline untuk Android.
Engine: llama-cpp-python (GGUF lokal). Tools: whitelist lokal. Network: diblokir total.
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import agent.sandbox  # WAJIB paling awal — blokir network
from tools.local_tools import TOOLS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.model_manager import model_path, list_models, set_active, get_active, CATALOG
from tools import skills as skillmod
MODEL = os.environ.get("LOKA_MODEL") or model_path()
CTX = int(os.environ.get("LOKA_CTX", "2048"))

SYSTEM = (
    "Kamu adalah Loka, asisten AI offline berbahasa Indonesia yang berjalan di ponsel pengguna. "
    "Jawab ringkas dan langsung. Kamu punya tool lokal: calc, note_save, note_list, note_read, "
    "file_write, file_read, file_list, now, battery. "
    "Jika perlu tool, jawab HANYA satu baris JSON: {\"tool\": \"nama\", \"args\": {...}} "
    "tanpa teks lain. Setelah hasil tool diberikan, jawab pertanyaan user dengan bahasa manusia. "
    "Kamu TIDAK punya akses internet dan tidak boleh mengaku bisa."
)

def reload_system_prompt(user_text=""):
    base = SYSTEM
    rel = skillmod.load_relevant(user_text)
    if rel: base += "\n\n[SKILL AKTIF — ikuti petunjuk ini]\n" + rel
    return base

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
        messages=[{"role":"system","content":reload_system_prompt(history[-1]["content"] if history else "")}] + history,
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
        except Exception:
            # JSON tool rusak (model kecil sering begitu) — paksa parse permissif
            try:
                txt = m.group(0)
                txt = re.sub(r",\s*}", "}", txt).replace("'", '"')
                call = json.loads(txt)
                name, args = call.get("tool"), call.get("args", {})
                result = TOOLS[name](**args) if name in TOOLS and isinstance(args, dict) else {"error":"tool tidak valid"}
                history.append({"role":"assistant","content":text})
                history.append({"role":"user","content":"[HASIL TOOL] " + json.dumps(result, ensure_ascii=False)})
                return step(history)
            except Exception:
                return text  # jawab apa adanya, jangan matikan sesi
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
        if q == "/model":
            for m in list_models():
                mark = "◀ aktif" if m["active"] else ("✓ ada" if m["downloaded"] else "belum unduh")
                print(f"  {m['key']:8s} {m['name']:28s} {m['size_mb']}MB  RAM {m['ram']}  {mark}")
            print("Ganti: /model <key>")
            continue
        if q.startswith("/model "):
            key = q.split()[1]
            try:
                r = set_active(key); print(f"Model aktif: {r['name']} (restart untuk memuat)")
            except ValueError as e: print(e)
            continue
        if q == "/skills": print(", ".join(skillmod.list_skills()) or "(kosong)"); continue
        if q.startswith("/skill "):
            print(skillmod.read_skill(q.split()[1]).get("content","?")); continue
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
