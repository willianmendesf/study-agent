#!/usr/bin/env python3
"""Baixa livros SOBRE ORACAO (PT-BR preferido) do z-library para _incoming/."""
import json, subprocess, sys, unicodedata
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
API = str(ROOT / "scripts" / "zlib-api.py")
DEST = ROOT / "data" / "biblioteca" / "_incoming"
CONTAS = ["zlib", "zlib2", "zlib3", "zlib4", "zlib5", "zlib6", "zlib7", "zlib8"]

# (rotulo, query de busca, palavras-chave obrigatorias no titulo, autor esperado)
ALVOS = [
    ("Bounds-Poder", "Poder Através da Oração E. M. Bounds", ["poder", "ora"], "bounds"),
    ("Bounds-Prega", "Pregação e Oração E. M. Bounds", ["prega"], "bounds"),
    ("Murray-Escola", "Escola de Oração Andrew Murray", ["escola"], "murray"),
    ("Murray-Espera", "Esperai no Senhor Andrew Murray", ["esperai"], "murray"),
    ("Murray-Intercessao", "A Intercessão do Espírito Andrew Murray", ["intercess"], "murray"),
    ("Torrey-ComoOrar", "Como Orar R. A. Torrey", ["como orar"], "torrey"),
    ("Torrey-Espirito", "O Espírito Santo R. A. Torrey", ["espirito santo"], "torrey"),
    ("Spurgeon-Oracao", "Oração Charles Spurgeon", ["ora"], "spurgeon"),
    ("Owen-Tentacao", "A Mortificação do Pecado John Owen", ["mortifica"], "owen"),
    ("Carson-Reforma", "Uma Chamada à Reforma Espiritual D. A. Carson", ["reforma"], "carson"),
    ("Packer-Orar", "Oração J. I. Packer", ["ora"], "packer"),
    ("Foster-Celebracao", "Celebração da Disciplina Richard Foster", ["celebra"], "foster"),
    ("Whitney-Disciplinas", "Disciplinas Espirituais Donald Whitney", ["disciplina"], "whitney"),
    ("Bonhoeffer-Salmos", "Os Salmos Dietrich Bonhoeffer", ["salmos"], "bonhoeffer"),
    ("Lutero-Oracao", "Uma Maneira Simples de Orar Martinho Lutero", ["orar"], "lutero"),
    ("Piper-Orar", "Orar é o melhor John Piper", ["orar"], "piper"),
    ("Tozer-Busca", "A Busca de Deus A. W. Tozer", ["busca"], "tozer"),
    ("Chadwick-Oracao", "Oração Samuel Chadwick", ["ora"], "chadwick"),
    ("Fenelon-Oracao", "Oração François Fénelon", ["ora"], "fenelon"),
    ("Agostinho-Confissoes", "Confissões Agostinho", ["confiss"], "agostinho"),
]


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return "-".join(w for w in "".join(c if c.isalnum() or c == " " else " " for c in s).split())[:70]


def busca(q):
    r = subprocess.run([sys.executable, API, "search", q, "--limit", "15"],
                       capture_output=True, text=True, timeout=180)
    try:
        return json.loads(r.stdout)
    except Exception:
        return []


def escolher(itens, kws, autor):
    melhor, score = None, -99
    for i in itens:
        if not isinstance(i, dict):
            continue
        t = (i.get("title") or "").lower()
        a = (i.get("author") or "").lower()
        s = 0.0
        if not any(k in t for k in kws):
            continue
        if autor and autor in a:
            s += 0.45
        if i.get("lang") == "Portuguese":
            s += 0.35
        elif i.get("lang") in ("English",):
            s -= 0.25
        if i.get("extension") == "epub":
            s += 0.20
        elif i.get("extension") == "pdf":
            s -= 0.10
        if any(x in t for x in ("box", "coleç", "coletânea", "obras completas", "volume 1-", "kit")):
            s -= 0.5
        if s > score:
            melhor, score = i, s
    return melhor, score


def baixa(rotulo, it):
    print(f"[{rotulo}] {it['title']} | {it.get('author')} | {it['extension']} | {it.get('lang')} id={it['id']}", flush=True)
    for conta in CONTAS:
        r = subprocess.run([sys.executable, API, "download", str(it["id"]), it["hash"], conta,
                            "--ext", it["extension"], "--dest", str(DEST)],
                           capture_output=True, text=True, timeout=900)
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            print(f"[{rotulo}] OK {conta} {out.strip()[:140]}", flush=True)
            return True
        if "daily limit" in out.lower() or "already reached" in out.lower():
            continue
        print(f"[{rotulo}] falhou {conta}: {out.strip()[:140]}", flush=True)
    print(f"[{rotulo}] NAO BAIXADO", flush=True)
    return False


ok = 0
feitos = set()
for rotulo, q, kws, autor in ALVOS:
    itens = busca(q)
    alvo, sc = escolher(itens, kws, autor)
    if not alvo or sc < 0.3:
        print(f"[{rotulo}] SEM CANDIDATO (score {sc})", flush=True)
        continue
    if alvo["id"] in feitos:
        print(f"[{rotulo}] JA BAIXADO nesta rodada (id {alvo['id']})", flush=True)
        continue
    if baixa(rotulo, alvo):
        ok += 1
        feitos.add(alvo["id"])
print(f"FIM baixados={ok}", flush=True)
