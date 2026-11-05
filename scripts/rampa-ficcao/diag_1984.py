#!/usr/bin/env python3
"""Diagnostico: converte Orwell-1984.epub em temp e testa marcadores distintivos.
Uso: python3 scripts/rampa-ficcao/diag_1984.py
"""
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
SRC = ROOT / "data/biblioteca/_incoming/Orwell-1984.epub"
EPUB2MD = ROOT / "data/perfil/bibliotecario/biblioteca-orbit/epub2md.py"


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


tmp = Path(tempfile.mkdtemp(prefix="diag1984-"))
r = subprocess.run([sys.executable, str(EPUB2MD), "--dest", str(tmp), str(SRC)],
                   capture_output=True, text=True, timeout=900)
mds = list(tmp.glob("*.md"))
print("mds:", [str(p) for p in mds])
m = max(mds, key=lambda p: p.stat().st_size)
txt = m.read_text(encoding="utf-8", errors="ignore")
corpo = sem_acento(txt).lower()
print("bytes:", m.stat().st_size, "linhas:", txt.count("\n"))
for marcador in ["1984", "nineteen eighty-four", "george orwell", "winston",
                 "novafala", "grande irmao", "partido", "telescreens",
                 "doublethink", "propaganda", "vigilancia", "comissario o'brien",
                 "salao de atas", "rodrigo silva", "julia", "vitoria"]:
    print(f"  {marcador!r:28s} -> {marcador in corpo}")
