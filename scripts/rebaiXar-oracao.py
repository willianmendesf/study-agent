#!/usr/bin/env python3
"""Re-baixa os originais dos livros de oracao (o cron de reenvio ao Orbit os
removeu de _incoming antes da conversao). Busca por titulo e casa pelo id."""
import json, subprocess, sys
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
API = str(ROOT / "scripts" / "zlib-api.py")
DEST = Path("/tmp/oracao-dl")
DEST.mkdir(exist_ok=True)
CONTAS = ["zlib4", "zlib5", "zlib6", "zlib7", "zlib8", "zlib3"]

ALVOS = [
    (12346777, "Poder Através da Oração Bounds"),
    (26731031, "Senhor, ensina-me a orar Murray"),
    (72968720, "Orando a palavra como orar como bíblia nos ensinou"),
    (21756102, "A Oração de Paulo Escola da Oração Spurgeon"),
    (22060618, "A Mortificação do Pecado John Owen"),
    (22109847, "Um Chamado a Reforma Espiritual Carson"),
    (5726737, "Celebração da Disciplina Richard Foster"),
    (22423480, "Em busca de Deus Tozer"),
    (125574839, "Gerando em oração Amanda Josepetti"),
    (126852764, "Devocional Quarto de Guerra"),
    (127506646, "A luta da oração Bloesch"),
    (49084043, "O privilégio da oração Arival Casimiro"),
    (123531349, "O poder da oração pelo casamento Elizabeth George"),
    (116144425, "O poder secreto da oração e do jejum Mahesh Chavda"),
    (21942514, "A oração Santo Afonso de Ligório"),
    (117398270, "Bíblia de Estudo Conciso Oração e Intercessão"),
    (22057740, "Comentário Bíblico Matthew Henry Salmos"),
]


def busca(q):
    r = subprocess.run([sys.executable, API, "search", q, "--limit", "20"],
                       capture_output=True, text=True, timeout=200)
    try:
        return [i for i in json.loads(r.stdout) if isinstance(i, dict)]
    except Exception:
        return []


def baixa(it):
    for conta in CONTAS:
        r = subprocess.run([sys.executable, API, "download", str(it["id"]), it["hash"], conta,
                            "--ext", it["extension"], "--dest", str(DEST)],
                           capture_output=True, text=True, timeout=900)
        if r.returncode == 0:
            return True
    return False


for alvo_id, q in ALVOS:
    existente = list(DEST.glob(f"zlib-{alvo_id}.*"))
    if existente:
        print(f"[JA TEM] {alvo_id} {existente[0].name}", flush=True)
        continue
    itens = busca(q)
    it = next((i for i in itens if i.get("id") == alvo_id), None)
    if not it:
        print(f"[SEM] {alvo_id} | {q} — nao achei o id na busca", flush=True)
        continue
    ok = baixa(it)
    print(f"[{'OK' if ok else 'FALHOU'}] {alvo_id} {it['title'][:60]}", flush=True)
print("FIM", flush=True)
