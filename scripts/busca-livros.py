#!/usr/bin/env python3
"""Busca por termos-chave nos .md da biblioteca (fallback quando buscar.py e bloqueado)."""
import sys, os, re, glob

def search(term, root="data/biblioteca", max_hits=25, ctx=260):
    pat = re.compile(term, re.I)
    hits = 0
    for path in glob.glob(root + "/**/*.md", recursive=True):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except Exception:
            continue
        # pula blocos de CSS (epub dump)
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if len(line) < 120 and not re.search(r"[a-zA-Z]{4}", line):
                continue
            if pat.search(line):
                print(f"--- {path}:{i+1}")
                print(re.sub(r"\s+", " ", line)[:ctx])
                hits += 1
                if hits >= max_hits:
                    return
    if hits == 0:
        print("SEM RESULTADO para:", term)

if __name__ == "__main__":
    term = sys.argv[1]
    root = sys.argv[2] if len(sys.argv) > 2 else "data/biblioteca"
    mx = int(sys.argv[3]) if len(sys.argv) > 3 else 25
    search(term, root, mx)
