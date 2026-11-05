#!/usr/bin/env python3
"""Lista obras de ficcao do acervo com tamanho, para montar trilha de leitura do menor ao maior."""
import glob, os

DIRS = [
    "/home/willian/study-agent/data/biblioteca/literatura-brasileira",
    "/home/willian/study-agent/data/biblioteca/literatura-mundial-classica",
    "/home/willian/study-agent/data/biblioteca/leitura-formacao",
    "/home/willian/study-agent/data/biblioteca/literatura",
]

rows = []
for d in DIRS:
    for f in sorted(glob.glob(d + "/*.md")):
        kb = os.path.getsize(f) / 1024
        rows.append((kb, os.path.basename(f)))

for kb, name in sorted(rows):
    print(f"{kb:8.0f} KB  {name}")
