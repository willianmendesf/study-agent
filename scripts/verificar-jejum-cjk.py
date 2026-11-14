#!/usr/bin/env python3
"""Varre caracteres nao-latinos (CJK, hangul, cirilico) nos .md de jejum."""
import re
import sys
from pathlib import Path

BIB = Path("/home/willian/study-agent/data/biblioteca/vida-crista")
ALVOS = [
    "A-cultura-do-jejum-Luciano-Subira.md",
    "Manual-Biblico-do-Jejum-JB-Carvalho.md",
    "Praticas-de-Jejum-Monsenhor-Jonas-Abib.md",
    "Em-Defesa-do-Jejum-Danilo-Balu.md",
    "Fome-por-Deus-John-Piper.md",
    "Gods-Chosen-Fast-A-Spiritual-Guide-to-Fasting-Arthur-Wallis.md",
    "Fasting-for-Spiritual-Breakthrough-A-Guide-to-Nine-Biblical-Fasts-Elmer-L-Towns.md",
    "A-Disciplina-Espiritual-e-as-Nossas-Atividades-Paul-Washer.md",
    "Jejum-como-encontrar-respostas-e-se-aproximar-de-Deus-John-Eckhardt.md",
    "O-Salterio-um-livro-de-oracoes-40-dias-de-Jejum-e-Oracao-Walmir-Vargas.md",
]
PAT = re.compile(r"[\u3000-\u9fff\uac00-\ud7af\u0400-\u04ff]")
total = 0
for nome in ALVOS:
    p = BIB / nome
    if not p.exists():
        print(f"? {nome}: ausente")
        continue
    txt = p.read_text(encoding="utf-8", errors="ignore")
    achados = PAT.findall(txt)
    if achados:
        total += len(achados)
        amostra = "".join(sorted(set(achados))[:20])
        print(f"X {nome}: {len(achados)} caractere(s) nao-latino(s) -> {amostra}")
    else:
        print(f"OK {nome}")
print(f"\ntotal de caracteres suspeitos: {total}")
sys.exit(1 if total else 0)
