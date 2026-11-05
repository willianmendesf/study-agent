#!/usr/bin/env python3
"""Descobre para onde o search redireciona (307) e testa o POST no destino."""
import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("zapi", HERE / "zlib-api.py")
Z = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Z)

acc = sys.argv[1] if len(sys.argv) > 1 else "zlib2"
ck = Z.cookies_for(acc)
d = Z._domain()


def head(method, path, extra=None, follow=False):
    args = ["-sS", "--max-time", "30", "-D", "-", "-o", "/dev/null",
            "-H", f"User-Agent: {Z.UA}", "-b", ck]
    if follow:
        args += ["-L"]
    if method == "POST":
        args += ["-X", "POST"]
    args += [f"{d}{path}"]
    if extra:
        args += extra
    r = subprocess.run(["curl"] + args, capture_output=True, text=True, timeout=60)
    print(f"=== {method} {path} follow={follow} ===")
    print(r.stdout[:1200])
    print()


head("POST", "/eapi/book/search", ["--data-urlencode", "message=Dumbo",
                                   "--data-urlencode", "limit=3"])
head("POST", "/eapi/book/search", ["--data-urlencode", "message=Dumbo",
                                   "--data-urlencode", "limit=3"], follow=True)
