#!/usr/bin/env python3
"""Testa: (a) GET no search, (b) POST em varios dominios, (c) diamwall cookie."""
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


def run(url, method="GET", extra=None, cookies=None):
    args = ["-sS", "--max-time", "30", "-w", "\n__HTTP=%{http_code}\n",
            "-H", f"User-Agent: {Z.UA}"]
    if cookies:
        args += ["-b", cookies]
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
    return out[:600]


print("### 1) GET search no dominio principal")
print(run("https://z-lib.sk/eapi/book/search?message=Dumbo&limit=3", cookies=ck))

print("\n### 2) GET search com cookie diamwall")
print(run("https://z-lib.sk/eapi/book/search?message=Dumbo&limit=3",
          cookies=ck + "; __diamwall=0x820095860"))

print("\n### 3) POST search com __diamwall pre-definido")
print(run("https://z-lib.sk/eapi/book/search", "POST",
          ["--data-urlencode", "message=Dumbo", "--data-urlencode", "limit=3"],
          cookies=ck + "; __diamwall=0x820095860"))

for dom in Z.DOMAINS[1:]:
    print(f"\n### 4) POST search em {dom}")
    o = run(f"{dom}/eapi/book/search", "POST",
            ["--data-urlencode", "message=Dumbo", "--data-urlencode", "limit=3"],
            cookies=ck)
    print(o)
    if '"success":1' in o:
        print(f"  >>> FUNCIONA: {dom}")
        break
