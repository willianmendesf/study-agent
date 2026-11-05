#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audita os simulados no Memos: quais tem gabarito vazando, tamanho, tags."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "/home/willian/study-agent/scripts")
import importlib.util

spec = importlib.util.spec_from_file_location(
    "curador", "/home/willian/study-agent/scripts/curador-memos.py")
cur = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cur)

cur.carregar_env()
todos = cur.listar()
meu = "users/willianmendesf"

sims = []
for m in todos:
    if (m.get("creator") or "") != meu:
        continue
    tags = cur.tags_de(m)
    if "tipo/simulado" not in tags and "simulado" not in tags:
        continue
    c = m.get("content") or ""
    gab_details = len(re.findall(r"<details", c))
    gab_sim = len(re.findall(r"<summary>\s*Gabarito", c))
    check = c.count("✅")
    titulo = (c.splitlines()[0] if c.strip() else "(vazio)")[:70]
    sims.append({
        "uid": cur.uid(m),
        "titulo": titulo,
        "len": len(c),
        "details": gab_details,
        "gabarito_blocks": gab_sim,
        "checks": check,
        "tags": tags,
        "content": c,
    })

print(f"TOTAL simulados Study-Agent: {len(sims)}\n")
for s in sims:
    print(f"- {s['uid']}")
    print(f"  titulo : {s['titulo']}")
    print(f"  bytes  : {s['len']}")
    print(f"  details: {s['details']}  gabarito-blocks: {s['gabarito_blocks']}  ✅: {s['checks']}")
    print(f"  tags   : {s['tags']}")
    print()

Path("/tmp/memos-simulados.json").write_text(
    json.dumps(sims, ensure_ascii=False, indent=1), encoding="utf-8")
print("salvo /tmp/memos-simulados.json")
