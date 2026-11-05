#!/usr/bin/env python3
"""Le a lista de aquisicao e mostra estrutura (headings + tabela ativa)."""
import sys, re, io

path = "data/" + "bibli" + "teca/lista-aquisicao.md"
with io.open(path, encoding="utf-8") as f:
    lines = f.readlines()

print("TOTAL LINHAS:", len(lines))
print("=" * 60)
for i, l in enumerate(lines, 1):
    if re.match(r"^#{1,3} ", l):
        print(f"{i:5d} {l.rstrip()}")
