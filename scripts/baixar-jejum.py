#!/usr/bin/env python3
"""Baixa livros DE e SOBRE JEJUM (PT-BR preferido) do z-library para _incoming/.

Os alvos foram escolhidos a mao a partir da busca real no z-library
(2026-11-14), descartando jejum intermitente/dieta e o que ja existe no acervo.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
API = str(ROOT / "scripts" / "zlib-api.py")
DEST = ROOT / "data" / "biblioteca" / "_incoming"
CONTAS = ["zlib", "zlib2", "zlib3", "zlib4", "zlib5", "zlib6", "zlib7", "zlib8"]

# (id, hash, extensao, rotulo, titulo, autor)
ALVOS = [
    (23047016, "0727fd", "epub", "Subira-Cultura",
     "A cultura do jejum", "Luciano Subira"),
    (23348082, "b7dfd2", "pdf", "Carvalho-Manual",
     "Manual Biblico do Jejum", "JB Carvalho"),
    (11832572, "a1a204", "epub", "Abib-Praticas",
     "Praticas de Jejum", "Monsenhor Jonas Abib"),
    (21239311, "b8afcb", "epub", "Balu-Defesa",
     "Em Defesa do Jejum", "Danilo Balu"),
    (5710082, "e5a007", "pdf", "Vargas-Salterio",
     "O Salterio: 40 dias de Jejum e oracao", "Walmir Vargas"),
    (29049500, "764462", "epub", "Piper-Fome",
     "Fome por Deus", "John Piper"),
    (18094941, "4f023a", "pdf", "Eckhardt-Jejum",
     "Jejum: como encontrar respostas e se aproximar de Deus", "John Eckhardt"),
    (12343568, "57a334", "epub", "Washer-Disciplina",
     "A Disciplina Espiritual e as Nossas Atividades", "Paul Washer"),
    (16781774, "e97fbc", "epub", "Wallis-GodsChosenFast",
     "God's Chosen Fast: A Spiritual Guide to Fasting", "Arthur Wallis"),
    (5894207, "630411", "epub", "Towns-Breakthrough",
     "Fasting for Spiritual Breakthrough", "Elmer L. Towns"),
]


def baixa(rotulo, bid, h, ext):
    for conta in CONTAS:
        r = subprocess.run(
            [sys.executable, API, "download", str(bid), h, conta,
             "--ext", ext, "--dest", str(DEST)],
            capture_output=True, text=True, timeout=900)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        if r.returncode == 0:
            print(f"[{rotulo}] OK {conta} {out[:160]}", flush=True)
            return True
        low = out.lower()
        if "daily limit" in low or "already reached" in low:
            continue
        print(f"[{rotulo}] falhou {conta}: {out[:160]}", flush=True)
    print(f"[{rotulo}] NAO BAIXADO", flush=True)
    return False


ok = 0
for bid, h, ext, rotulo, titulo, autor in ALVOS:
    if baixa(rotulo, bid, h, ext):
        ok += 1
print(f"FIM baixados={ok}/{len(ALVOS)}", flush=True)
