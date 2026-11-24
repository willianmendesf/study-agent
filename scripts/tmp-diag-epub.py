#!/usr/bin/env python3
"""Diagnostico: por que 0 chars em 2 EPUBs (Tozer, Spurgeon) + converter Carson PDF."""
import sys, zipfile
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
INC = ROOT / "data/biblioteca/_incoming"

for nome in ["zlib-22423480.epub", "zlib-21756102.epub"]:
    p = INC / nome
    print("=" * 60)
    print(nome, p.stat().st_size // 1024, "KB")
    try:
        z = zipfile.ZipFile(p)
        nomes = z.namelist()
        print("  itens:", len(nomes))
        exts = {}
        for n in nomes:
            e = n.rsplit(".", 1)[-1].lower() if "." in n else "?"
            exts[e] = exts.get(e, 0) + 1
        print("  tipos:", exts)
        htmls = [n for n in nomes if n.lower().endswith((".html", ".xhtml", ".htm"))]
        print("  htmls:", len(htmls), htmls[:5])
        tot = 0
        for n in htmls[:3]:
            tot += len(z.read(n))
        print("  bytes primeiros 3 htmls:", tot)
        # amostra de texto cru
        if htmls:
            amostra = z.read(htmls[0]).decode("utf-8", "ignore")
            print("  amostra:", amostra[:300].replace("\n", " "))
    except Exception as e:
        print("  ERRO:", e)
