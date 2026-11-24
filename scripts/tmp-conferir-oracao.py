#!/usr/bin/env python3
"""Converte os arquivos novos de _incoming (livros de oracao) e mostra o
inicio do texto para CONFERIR titulo/autor antes de nomear e catalogar."""
import subprocess, sys, tempfile
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
ORBIT = ROOT / "data/perfil/bibliotecario/biblioteca-orbit"
INC = ROOT / "data/biblioteca/_incoming"
TMP = Path("/tmp/conv-oracao")
TMP.mkdir(exist_ok=True)

ARQS = sys.argv[1:]

for nome in ARQS:
    src = INC / nome
    if not src.exists():
        print(f"### {nome}: AUSENTE")
        continue
    r = subprocess.run([sys.executable, str(ORBIT / "epub2md.py"), str(src), "--dest", str(TMP)],
                       capture_output=True, text=True, timeout=900)
    out = (r.stdout or "") + (r.stderr or "")
    gerados = sorted(TMP.glob("*.md"), key=lambda p: p.stat().st_mtime)
    print("=" * 70)
    print(f"### {nome} ({src.stat().st_size//1024} KB)")
    print(out.strip()[-400:])
    if not gerados:
        print("   SEM MD")
        continue
    md = gerados[-1]
    txt = md.read_text(encoding="utf-8", errors="ignore")
    print(f"   md: {md.name} | {len(txt)} chars | {txt.count(chr(10))} linhas")
    linhas = [l.strip() for l in txt.split("\n") if l.strip()][:14]
    for l in linhas:
        print("   |", l[:110])
    md.unlink()
print("FIM")
