#!/usr/bin/env python3
"""Atualiza tamanho_md e linhas_md na KB de literatura com os valores REAIS dos arquivos.

Motivo: o lote da rampa (2026-11-05) catalogou as entradas no 1o passe, antes da
normalizacao de OCR. Os arquivos foram reescritos depois (letras espacadas juntas),
entao as contagens ficaram defasadas. O conteudo esta correto; so os metadados
da KB estavam errados.

Uso: python3 scripts/rampa-ficcao/corrigir_metadados_kb.py [--dry-run]
"""
import re
import sys
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
KB = ROOT / "data/biblioteca/global/kb-literatura.yaml"

dry = "--dry-run" in sys.argv
txt = KB.read_text(encoding="utf-8")

padrao = re.compile(
    r"(  - titulo: .+?\n    caminho_md: (?P<cam>.+?)\n)"
    r"    tamanho_md: .+?\n"
    r"    linhas_md: \d+\n")

mudancas = []


def sub(m):
    caminho = m.group("cam")
    p = ROOT / caminho.lstrip("./")
    if not p.exists():
        return m.group(0)
    real_tam = p.stat().st_size // 1024
    real_lin = len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
    novo = (m.group(1)
            + f"    tamanho_md: {real_tam} KB\n"
            + f"    linhas_md: {real_lin}\n")
    if novo != m.group(0):
        mudancas.append((caminho.strip(), real_tam, real_lin))
    return novo


novo_txt = padrao.sub(sub, txt)

if dry:
    print(f"[dry-run] {len(mudancas)} entrada(s) a corrigir")
    for c, t, l in mudancas:
        print(f"  {c}")
    sys.exit(0)

KB.write_text(novo_txt, encoding="utf-8")
print(f"{len(mudancas)} entrada(s) corrigida(s) em {KB.relative_to(ROOT)}")
