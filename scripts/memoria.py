#!/usr/bin/env python3
"""Consulta a memória entre sessões (deja) — wrapper tolerante a falhas."""
import os, subprocess, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(RAIZ, ".claude", "skills", "deja-search", "bin", "linux_amd64", "deja")

def main():
    if not os.path.exists(BIN):
        print("binário do deja não encontrado:", BIN, file=sys.stderr)
        return 2
    cmd = [BIN] + sys.argv[1:]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=RAIZ)
    except Exception as e:
        print("ERRO:", e, file=sys.stderr)
        return 1
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    if out:
        print(out[:6000])
    if err:
        print("--- stderr ---", file=sys.stderr)
        print(err[:2000], file=sys.stderr)
    return r.returncode

if __name__ == "__main__":
    sys.exit(main())
