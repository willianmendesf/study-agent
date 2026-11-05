#!/usr/bin/env python3
"""Testa: search sem cookie / com cookie jar (DiamWall) / download autenticado."""
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("zapi", HERE / "zlib-api.py")
Z = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Z)

acc = "zlib2"
ck = Z.cookies_for(acc)
envs = Z.load_accounts()


def run(url, method="POST", extra=None, cookies=None, jar=None):
    args = ["-sS", "--max-time", "25", "-w", "\n__HTTP=%{http_code}\n",
            "-H", f"User-Agent: {Z.UA}"]
    if cookies:
        args += ["-b", cookies]
    if jar:
        args += ["-b", jar, "-c", jar]
    if method == "POST":
        args += ["-X", "POST"]
    args += [url]
    if extra:
        args += extra
    try:
        r = subprocess.run(["curl"] + args, capture_output=True, text=True, timeout=60)
        out = r.stdout
    except Exception as e:
        return f"EXC {e}"
    for e in envs.values():
        out = out.replace(e["ZLIB_REMIX_KEY"], "***")
    return out


DOM = "https://z-lib.sk"

print("### A) search SEM cookie de sessao")
o = run(f"{DOM}/eapi/book/search", "POST",
        ["--data-urlencode", "message=Orgulho e Preconceito Austen",
         "--data-urlencode", "limit=3"])
print(o[:500])

print("\n### B) search SEM cookie, com cookie JAR (retenta se 307)")
jar = tempfile.mktemp(prefix="zjar")
for i in range(3):
    o = run(f"{DOM}/eapi/book/search", "POST",
            ["--data-urlencode", "message=Orgulho e Preconceito Austen",
             "--data-urlencode", "limit=3"], jar=jar)
    print(f"  tentativa {i+1}: {o[:200]}")
    if '"success":1' in o:
        break

print("\n### C) search COM remix cookie + jar")
jar2 = tempfile.mktemp(prefix="zjar2")
for i in range(3):
    o = run(f"{DOM}/eapi/book/search", "POST",
            ["--data-urlencode", "message=Orgulho e Preconceito Austen",
             "--data-urlencode", "limit=3"], cookies=ck, jar=jar2)
    print(f"  tentativa {i+1}: {o[:200]}")
    if '"success":1' in o:
        break
