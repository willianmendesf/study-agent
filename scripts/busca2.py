#!/usr/bin/env python3
"""Busca por termos-chave nos .md da biblioteca (fallback quando buscar.py e bloqueado).
Uso: python3 busca2.py "<regex>" <dir|arquivo.md> [max_hits] [min_len]
"""
import sys, os, re, glob

def files_for(root):
    if os.path.isfile(root):
        return [root]
    return sorted(glob.glob(root + "/**/*.md", recursive=True))

def search(term, root, max_hits=25, min_len=0):
    pat = re.compile(term, re.I)
    hits = 0
    for path in files_for(root):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.read().split("\n")
        except Exception:
            continue
        for i, line in enumerate(lines):
            if len(line) < min_len:
                continue
            if pat.search(line):
                print(f"--- {os.path.basename(path)}:{i+1}")
                print(re.sub(r"\s+", " ", line)[:400])
                hits += 1
                if hits >= max_hits:
                    return hits
    if hits == 0:
        print("SEM RESULTADO para:", term)
    return hits

if __name__ == "__main__":
    term = sys.argv[1]
    root = sys.argv[2]
    mx = int(sys.argv[3]) if len(sys.argv) > 3 else 25
    ml = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    search(term, root, mx, ml)
