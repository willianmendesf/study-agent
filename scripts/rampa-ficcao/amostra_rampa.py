#!/usr/bin/env python3
"""Amostra os primeiros parágrafos de cada .md novo da rampa para conference visual.
Uso: python3 scripts/rampa-ficcao/amostra_rampa.py
"""
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
DEST = ROOT / "data/biblioteca/literatura-mundial-classica"

NOVOS = [
    "dostoievski/Crime-e-Castigo-Fiodor-Dostoievski.md",
    "dostoievski/Os-Irmaos-Karamazov-Fiodor-Dostoievski.md",
    "dostoievski/O-Idiota-Fiodor-Dostoievski.md",
    "dostoievski/Os-Demonios-Fiodor-Dostoievski.md",
    "dostoievski/O-Jogador-Fiodor-Dostoievski.md",
    "tolstoi/Guerra-e-Paz-Lev-Tolstoi.md",
    "tolstoi/Anna-Karenina-Lev-Tolstoi.md",
    "tolstoi/Ressurreicao-Lev-Tolstoi.md",
    "austen/Orgulho-e-Preconceito-Jane-Austen.md",
    "austen/Emma-Jane-Austen.md",
    "bronte/Jane-Eyre-Charlotte-Bronte.md",
    "anglo-saxoes/Middlemarch-George-Eliot.md",
    "anglo-saxoes/Moby-Dick-Herman-Melville.md",
    "anglo-saxoes/Frankenstein-Mary-Shelley.md",
    "anglo-saxoes/Mrs-Dalloway-Virginia-Woolf.md",
    "anglo-saxoes/As-Aventuras-de-Tom-Sawyer-Mark-Twain.md",
    "anglo-saxoes/As-Aventuras-de-Huckleberry-Finn-Mark-Twain.md",
    "anglo-saxoes/1984-George-Orwell.md",
    "anglo-saxoes/A-Revolucao-dos-Animais-George-Orwell.md",
    "dickens/Grandes-Esperancas-Charles-Dickens.md",
    "dickens/Casa-de-Cassandra-Charles-Dickens.md",
    "dickens/David-Copperfield-Charles-Dickens.md",
    "agostinho/A-Cidade-de-Deus-Santo-Agostinho.md",
    "agostinho/Confissoes-Santo-Agostinho.md",
    "dante/A-Divina-Comedia-Dante-Alighieri.md",
    "antigos/A-Odisseia-Homero.md",
    "antigos/A-Eneida-Virgilio.md",
    "antigos/Fausto-Johann-Wolfgang-von-Goethe.md",
    "proust/Em-Busca-do-Tempo-Perdido-I-Marcel-Proust.md",
    "frances/Madame-Bovary-Gustave-Flaubert.md",
]

for rel in NOVOS:
    p = DEST / rel
    if not p.exists():
        print(f"### {rel}\n   !! AUSENTE\n")
        continue
    txt = p.read_text(encoding="utf-8", errors="ignore")
    if txt.lstrip().startswith("---"):
        fm = txt.split("---", 2)[1]
        corpo = txt.split("---", 2)[2]
        linha_t = [l for l in fm.splitlines() if l.startswith("titulo")]
        linha_a = [l for l in fm.splitlines() if l.startswith("autor")]
    else:
        corpo = txt
        linha_t = linha_a = ["(sem frontmatter)"]
    linhas = [l.strip() for l in corpo.strip().splitlines() if l.strip()]
    amostra = " ".join(linhas[1:4])[:230] if len(linhas) > 3 else " ".join(linhas[:3])[:230]
    print(f"### {rel}")
    print(f"    {linha_t[0]} | {linha_a[0]} | {p.stat().st_size//1024} KB")
    print(f"    > {amostra}\n")
