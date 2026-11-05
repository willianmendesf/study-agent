#!/usr/bin/env python3
"""Mapeia quais dominios do Z-Library respondem search de verdade (com sessao)."""
import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("zapi", HERE / "zlib-api.py")
Z = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Z)

acc = "zlib2"
ck = Z.cookies_for(acc)
envs = Z.load_accounts()

CAND = [
    "https://z-lib.gd", "https://z-lib.sk", "https://z-lib.es", "https://z-lib.rs",
    "https://z-lib.fm", "https://z-lib.se", "https://z-lib.la", "https://z-lib.li",
    "https://z-lib.cz", "https://z-lib.su", "https://z-lib.org", "https://z-lib.net",
    "https://z-lib.io", "https://z-lib.ink", "https://z-lib.vg", "https://z-lib.website",
]

for d in CAND:
    args = ["curl", "-sS", "--max-time", "15", "-X", "POST", f"{d}/eapi/book/search",
            "-H", f"User-Agent: {Z.UA}", "-b", ck,
            "--data-urlencode", "message=Orgulho e Preconceito Austen",
            "--data-urlencode", "limit=3"]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=40)
        out = r.stdout
    except Exception as e:
        print(f"{d:34s} EXC {str(e)[:60]}")
        continue
    if '"success":1' in out:
        n = out.count('"id"')
        print(f"{d:34s} OK  ({n} resultados)")
    else:
        tag = "307/diamwall" if "307" in out or "DiamWall" in out else out[:80].replace("\n", " ")
        print(f"{d:34s} -- {tag}")
