#!/usr/bin/env python3
"""Debug da eAPI do Z-Library: mostra status HTTP e corpo SEM segredo."""
import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("zapi", HERE / "zlib-api.py")
Z = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Z)

acc = sys.argv[1] if len(sys.argv) > 1 else "zlib2"
d = Z._domain()
print("dominio:", d)
ck = Z.cookies_for(acc)
envs = Z.load_accounts()


def raw(method, path, extra=None):
    args = ["-sS", "--max-time", "30", "-w", "\n__HTTP=%{http_code}\n",
            "-H", f"User-Agent: {Z.UA}", "-b", ck]
    if method == "POST":
        args += ["-X", "POST"]
    args += [f"{d}{path}"]
    if extra:
        args += extra
    try:
        r = subprocess.run(["curl"] + args, capture_output=True, text=True, timeout=60)
        out = r.stdout
    except Exception as e:
        print(f"--- {method} {path} --- EXC {e}\n")
        return
    for e in envs.values():
        out = out.replace(e["ZLIB_REMIX_KEY"], "***")
    print(f"--- {method} {path} ---")
    print(out[:900])
    print()


raw("POST", "/eapi/user/login", ["--data-urlencode", "email=x", "--data-urlencode", "password=x"])
raw("GET", "/eapi/user/profile")
raw("POST", "/eapi/book/search", ["--data-urlencode", "message=Dumbo", "--data-urlencode", "limit=3"])
