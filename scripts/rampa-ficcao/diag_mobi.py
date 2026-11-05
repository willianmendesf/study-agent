#!/usr/bin/env python3
"""Diagnostico: converte Orwell-A-Revolucao-dos-Animais.mobi e mostra o inicio.
Uso: python3 scripts/rampa-ficcao/diag_mobi.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
SRC = ROOT / "data/biblioteca/_incoming/Orwell-A-Revolucao-dos-Animais.mobi"
EPUB2MD = ROOT / "data/perfil/bibliotecario/biblioteca-orbit/epub2md.py"

print("origem:", SRC, SRC.stat().st_size, "bytes")
tmp = Path(tempfile.mkdtemp(prefix="diagmobi-"))
r = subprocess.run([sys.executable, str(EPUB2MD), "--dest", str(tmp), str(SRC)],
                   capture_output=True, text=True, timeout=900)
print("stdout:", r.stdout[-400:])
print("stderr:", r.stderr[-400:])
mds = list(tmp.glob("*.md"))
print("mds:", [str(p) for p in mds])
for m in mds:
    txt = m.read_text(encoding="utf-8", errors="ignore")
    print("=" * 60)
    print(m.name, m.stat().st_size, "bytes,", txt.count("\n"), "linhas")
    print(txt[:1200])
