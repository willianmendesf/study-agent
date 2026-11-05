#!/usr/bin/env python3
"""Completa o frontmatter de .md da biblioteca que tem titulo+tags mas falta autor.

NAO mexe em arquivos que ja tem autor. NAO mexe em conteudo (so o frontmatter).

Uso: python3 scripts/rampa-ficcao/completar_autor_frontmatter.py [--dry-run]
"""
import re
import sys
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
BIB = ROOT / "data/biblioteca"

# (caminho relativo, autor a acrescentar)
ALVOS = [
    ("literatura/LT-Como-ler-livros-Portu.md",
     "Mortimer J. Adler e Charles Van Doren"),
    ("literatura/Como-ler-livros-Mortimer-Jerome-Adler-Charles-van-Doren.md",
     "Mortimer J. Adler e Charles Van Doren"),
    ("literatura/Homens-de-verdade-o-chamado-de-Deus-para-masculinidade-Phillips-Richard-D.md",
     "Richard D. Phillips"),
    ("literatura/Reformando-a-Familia-Conselhos-para-um-Lar-Cristao-Richard-Baxter.md",
     "Richard Baxter"),
]

dry = "--dry-run" in sys.argv
for rel, autor in ALVOS:
    p = BIB / rel
    if not p.exists():
        print(f"[ausente] {rel}")
        continue
    txt = p.read_text(encoding="utf-8", errors="ignore")
    if not txt.lstrip().startswith("---"):
        print(f"[sem frontmatter] {rel}")
        continue
    partes = txt.split("---", 2)
    fm = partes[1]
    if re.search(r"^autor:", fm, re.M):
        print(f"[ja tem autor] {rel}")
        continue
    novo_fm = re.sub(r'^(titulo: .*)$', r'\1\nautor: "%s"' % autor,
                      fm, count=1, flags=re.M)
    novo = "---" + novo_fm + "---" + partes[2]
    if dry:
        print(f"[dry-run] {rel}: acrescentaria autor={autor!r}")
        continue
    p.write_text(novo, encoding="utf-8")
    print(f"[ok] {rel}: autor={autor!r}")
