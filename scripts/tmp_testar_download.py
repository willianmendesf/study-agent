#!/usr/bin/env python3
"""Testa UM download real end-to-end (search -> file -> downloadLink -> baixa)."""
import json
import re
import subprocess
import types
import unicodedata
from pathlib import Path

src = Path("/home/willian/study-agent/scripts/tmp_baixar_rampa.py").read_text(encoding="utf-8")
cut = src.split('print(f"ALVOS:')[0]
mod = types.ModuleType("dl")
exec(compile(cut, "dl", "exec"), mod.__dict__)

v2src = Path("/home/willian/study-agent/scripts/tmp_selecionar_v2.py").read_text(encoding="utf-8")
v2cut = v2src.split("TESTES = [")[0]
mod2 = types.ModuleType("dl2")
exec(compile(v2cut, "dl2", "exec"), mod2.__dict__)

books = mod.busca("Crime e Castigo Dostoiévski", "zlib")
cand, sc = mod2.melhor2(books, "Crime e Castigo", "Dostoiévski", "Crime and Punishment")
print("candidato:", cand.get("id"), cand.get("hash"), cand.get("title"), cand.get("extension"))

# passo 1: pega link
out = mod.curl([f"https://{mod.DOM}/eapi/book/{cand['id']}/{cand['hash']}/file",
                 "-H", f"User-Agent: {mod.UA}", "-b", mod.cookie("zlib")], timeout=45)
d = json.loads(out)
print("success:", d.get("success"))
link = d.get("file", {}).get("downloadLink")
ext = d.get("file", {}).get("extension")
print("ext:", ext, "| link host:", link.split("/")[2] if link else None)
if not link:
    print("RESPOSTA COMPLETA:", out[:600])
    raise SystemExit(1)

dest = mod.INCOMING / f"TESTE-Crime-e-Castigo.{ext}"
r = subprocess.run(["curl", "-sSL", "-m", "300", "-o", str(dest),
                    "-H", f"User-Agent: {mod.UA}", link], capture_output=True, text=True)
print("curl rc:", r.returncode, r.stderr[:200])
print("dest existe:", dest.exists(), "| tamanho:", dest.stat().st_size if dest.exists() else 0)
if dest.exists() and dest.stat().st_size > 20000:
    with dest.open("rb") as f:
        head = f.read(4)
    print("magic:", head, "(PK.. = zip/epub)")
    print("cota depois:")
    out2 = mod.curl([f"https://{mod.DOM}/eapi/user/profile", "-H", f"User-Agent: {mod.UA}",
                     "-b", mod.cookie("zlib")], timeout=30)
    u = json.loads(out2).get("user", {})
    print("  hoje =", u.get("downloads_today"), "/", u.get("downloads_limit"))
