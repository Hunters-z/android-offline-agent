"""Sistem skill Loka: file markdown di ~/loka/skills/ — dimuat ke prompt saat relevan."""
import os, glob

SKILLS_DIR = os.path.join(os.environ.get("LOKA_HOME", os.path.expanduser("~/loka")), "skills")

def list_skills():
    os.makedirs(SKILLS_DIR, exist_ok=True)
    return [os.path.basename(p) for p in glob.glob(os.path.join(SKILLS_DIR, "*.md"))]

def read_skill(name):
    p = os.path.join(SKILLS_DIR, name if name.endswith(".md") else name+".md")
    if not os.path.realpath(p).startswith(os.path.realpath(SKILLS_DIR)):
        return {"error":"nama skill tidak valid"}
    if not os.path.exists(p): return {"error": f"skill '{name}' tidak ada"}
    return {"name": os.path.basename(p), "content": open(p).read()[:4000]}

def load_relevant(user_text, max_skills=2, max_chars=3000):
    """Heuristik kata kunci di frontmatter skill (keywords: ...) — tanpa network."""
    chosen, used = [], 0
    for path in sorted(glob.glob(os.path.join(SKILLS_DIR, "*.md"))):
        head = open(path).read(400)
        for kw in _extract_keywords(head):
            if kw in user_text.lower():
                chosen.append(open(path).read()[:1500]); used += 1500
                break
        if len(chosen) >= max_skills or used >= max_chars: break
    return "\n\n---\n".join(chosen)

def _extract_keywords(head):
    for line in head.splitlines():
        if line.lower().startswith("keywords:"):
            return [k.strip().lower() for k in line.split(":",1)[1].split(",")]
    return []
