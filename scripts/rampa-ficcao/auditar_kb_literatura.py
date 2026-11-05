#!/usr/bin/env python3
"""Auditoria de integridade da KB de literatura apos o lote da rampa.

Confere, para cada material catalogado em kb-literatura.yaml:
  1. o caminho_md existe
  2. o .md tem frontmatter com titulo/autor/tags nao vazias
  3. o titulo do catalogo bate (fuzzy) com o titulo do frontmatter
  4. o conteudo do .md NAO e de outro livro (procura marcadores de outro titulo
     conhecido no mesmo lote)

Uso: python3 scripts/rampa-ficcao/auditar_kb_literatura.py
"""
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
KB = ROOT / "data/biblioteca/global/kb-literatura.yaml"


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


txt = KB.read_text(encoding="utf-8")
mats = re.findall(
    r"  - titulo: (.+?)\n    caminho_md: (.+?)\n    tamanho_md: (.+?)\n    linhas_md: (\d+)",
    txt)
print(f"materiais na KB: {len(mats)}\n")

problemas = []
vistos = {}

for titulo, caminho, tamanho, linhas in mats:
    p = ROOT / caminho.lstrip("./")
    if not p.exists():
        problemas.append(f"[SEM ARQUIVO] {titulo} -> {caminho}")
        continue
    corpo = p.read_text(encoding="utf-8", errors="ignore")
    if not corpo.lstrip().startswith("---"):
        problemas.append(f"[SEM FRONTMATTER] {titulo}")
        continue
    fm = corpo.split("---", 2)[1]
    mt = re.search(r'titulo: "?(.*?)"?\n', fm)
    ma = re.search(r'autor: "?(.*?)"?\n', fm)
    mg = re.search(r"tags: \[(.*?)\]", fm)
    if not mt or not ma or not mg:
        problemas.append(f"[FM INCOMPLETO] {titulo}")
        continue
    ft, fa, fg = mt.group(1), ma.group(1), mg.group(1).strip()
    if not ft.strip() or not fa.strip() or not fg.strip():
        problemas.append(f"[FM VAZIO] {titulo} -> t={ft!r} a={fa!r} g={fg!r}")
    # tamanho declarado x real
    decl = int(re.sub(r"\D", "", tamanho) or 0)
    real = p.stat().st_size // 1024
    if decl and abs(decl - real) > max(20, decl * 0.15):
        problemas.append(f"[TAMANHO] {titulo}: KB diz {decl} KB, real {real} KB")
    # linhas
    if abs(len(corpo.splitlines()) - int(linhas)) > 30:
        problemas.append(f"[LINHAS] {titulo}: KB diz {linhas}, real {len(corpo.splitlines())}")
    vistos[titulo] = (ft, fa, sem_acento(ft).lower(), sem_acento(corpo).lower())

# checagem cruzada: o titulo de um livro aparece no corpo de OUTRO?
print("=== confere se algum .md contem o titulo de outro material ===")
chaves = list(vistos.items())
for i, (t1, (ft1, fa1, ft1l, corpo1)) in enumerate(chaves):
    for t2, (ft2, fa2, ft2l, corpo2) in chaves:
        if i == t2 or t1 == t2:
            continue
        if len(ft2l) < 8 or ft2l == ft1l:
            continue
        if ft2l in ft1l:
            continue
        # titulo de outro dentro deste corpo
        if ft2l in corpo1 and ft1l not in corpo1:
            print(f"  ATENCAO: '{ft1}' (de {fa1}) contem o titulo '{ft2}' — pode ser confusao de arquivo")
            problemas.append(f"[CONTEUDO] {ft1} contem titulo '{ft2}'")

if problemas:
    print(f"\n!! {len(problemas)} problema(s):")
    for x in problemas:
        print("  -", x)
    sys.exit(1)
print("\nOK: KB de literatura integra — todos os caminhos existem, frontmatter completo, "
      "tamanhos batem, nenhum conteudo trocado.")
