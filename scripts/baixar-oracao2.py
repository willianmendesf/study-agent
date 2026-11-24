#!/usr/bin/env python3
"""2a leva: buscas genericas por oracao, so PT, descarta EN/ES e repetidos."""
import json, subprocess, sys
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
API = str(ROOT / "scripts" / "zlib-api.py")
DEST = ROOT / "data" / "biblioteca" / "_incoming"
CONTAS = ["zlib2", "zlib3", "zlib4", "zlib5", "zlib6", "zlib7", "zlib8"]
JA = {12346777, 26731031, 72968720, 21756102, 22060618, 22109847, 16758940,
      5726737, 29638874, 22423480, 117111472}

QUERIES = [
    "oração",
    "orar",
    "vida de oração",
    "intercessão",
    "oração e jejum",
    "livro de oração cristão",
    "comunhão com Deus oração",
    "oração puritana",
    "salmos oração comentário",
    "pai nosso exposição",
    "oração reformada",
    "oração avivamento",
    "aprender a orar",
    "segredo da oração",
    "poder da oração",
]


def busca(q):
    r = subprocess.run([sys.executable, API, "search", q, "--limit", "20"],
                       capture_output=True, text=True, timeout=200)
    try:
        d = json.loads(r.stdout)
        return [i for i in d if isinstance(i, dict)]
    except Exception:
        return []


def baixa(it):
    for conta in CONTAS:
        r = subprocess.run([sys.executable, API, "download", str(it["id"]), it["hash"], conta,
                            "--ext", it["extension"], "--dest", str(DEST)],
                           capture_output=True, text=True, timeout=900)
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            return True, conta
        if "daily limit" in out.lower() or "already reached" in out.lower():
            continue
    return False, ""


vistos = set(JA)
novos = []
for q in QUERIES:
    for i in busca(q):
        if i["id"] in vistos:
            continue
        t = (i.get("title") or "").lower()
        a = (i.get("author") or "").lower()
        if not ("ora" in t or "orar" in t or "intercess" in t or "pai nosso" in t or "salmo" in t):
            continue
        if i.get("lang") not in ("Portuguese", "Brazilian"):
            continue
        if any(x in t for x in ("box", "coleç", "obras completas", "kit", "trilogia")):
            continue
        if i.get("extension") not in ("epub", "pdf"):
            continue
        vistos.add(i["id"])
        novos.append(i)

# dedupe por titulo normalizado
vistos_t = set()
final = []
for i in sorted(novos, key=lambda x: (x.get("extension") != "epub", -(x.get("year") or 0))):
    k = "".join(c for c in (i.get("title") or "").lower() if c.isalnum())[:45]
    if k in vistos_t:
        continue
    vistos_t.add(k)
    final.append(i)

print(f"candidatos PT: {len(final)}", flush=True)
ok = 0
for i in final:
    if ok >= 12:
        break
    print(f"-> {i['title']} | {i.get('author')} | {i['extension']} | {i.get('lang')} id={i['id']}", flush=True)
    r, conta = baixa(i)
    if r:
        ok += 1
        print(f"   OK {conta}", flush=True)
    else:
        print("   FALHOU", flush=True)
print(f"FIM2 baixados={ok}", flush=True)
