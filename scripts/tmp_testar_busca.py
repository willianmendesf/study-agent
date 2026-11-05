#!/usr/bin/env python3
"""Valida o pipeline de download do z-library com 3 alvos (dry-run do fluxo real)."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/home/willian/study-agent/scripts")
import importlib.util
spec = importlib.util.spec_from_file_location("dl", "/home/willian/study-agent/scripts/tmp_baixar_rampa.py")

# importa o modulo sem executar o laco principal -> nao roda porque esta sob __main__
import types
src = Path("/home/willian/study-agent/scripts/tmp_baixar_rampa.py").read_text(encoding="utf-8")
cut = src.split("print(f\"ALVOS:")[0]
mod = types.ModuleType("dl")
exec(compile(cut, "dl", "exec"), mod.__dict__)

for acct in mod.CONTAS:
    print("conta", acct, "->", mod.usa_conta(acct))

TESTES = [
    ("TESTE-Dostoyevsky", "Crime e Castigo Dostoiévski", "Crime e Castigo", "Dostoiévski", "Crime and Punishment"),
    ("TESTE-Tolstoi", "Guerra e Paz Tolstói", "Guerra e Paz", "Tolstói", "War and Peace"),
    ("TESTE-Austen", "Orgulho e Preconceito Jane Austen", "Orgulho e Preconceito", "Austen", "Pride and Prejudice"),
]

for slug, q, tit, aut, alt in TESTES:
    books = mod.busca(q, "zlib")
    print(f"\n--- {slug}: {len(books)} resultados")
    for b in books[:6]:
        print(f"    id={b.get('id')} ext={b.get('extension'):6s} {b.get('filesizeString','?'):9s} "
              f"| {b.get('title')[:55]} | {b.get('author')[:28]} | lang={b.get('language')}")
    cand, score = mod.melhor(books, tit, aut, alt)
    print(f"    ESCOLHIDO score={score}: {cand.get('title') if cand else None} "
          f"| {cand.get('author') if cand else None} | lang={cand.get('language') if cand else None} "
          f"| ext={cand.get('extension') if cand else None}")
