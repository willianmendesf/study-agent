#!/usr/bin/env python3
"""Conta palavras de cada obra de ficcao (remove blocos de CSS de dumps epub)."""
import glob, os, re

OBRAS = [
    "literatura-brasileira/Jose-de-Alencar-Iracema.md",
    "literatura-brasileira/Graciliano-Ramos-Vidas-Secas.md",
    "literatura-brasileira/Machado-Assis-Dom-Casmurro.md",
    "literatura-brasileira/Dom-Casmurro-Machado-de-Assis-ARVITEC.md",
    "literatura-brasileira/Memorias-Postumas-de-Bras-Cubas-Machado-de-Assis.md",
    "literatura-brasileira/A-Hora-da-Estrela-Clarice-Lispector.md",
    "literatura-brasileira/Lima-Barreto-Triste-Fim-de-Policarpo-Quaresma.md",
    "literatura-brasileira/Euclides-Cunha-Os-Sertoes.md",
    "literatura-brasileira/Guimaraes-Rosa-Grande-Sertao-Veredas.md",
    "literatura-mundial-classica/Cervantes-Dom-Quixote.md",
    "literatura-mundial-classica/The-Charles-Dickens-Collection-Volume-One-Oliver-Twist-Great-Expectations-and-Bleak-House.md",
    "literatura-mundial-classica/Brothers-Karamazov-Dostoyevsky-Fyodor-Dostoyevsky.md",
    "literatura-mundial-classica/War-And-Peace-Tolstoy-Leo-Tolstoy.md",
    "literatura-mundial-classica/Divine-Comedy-Dante-Alighieri-Dante-Alighieri-Robin-Kirkpatrick.md",
    "literatura-mundial-classica/Confessions-Augustine-Saint-Augustine-Henry-Chadwick.md",
    "literatura-mundial-classica/City-of-God-Augustine.md",
]

BASE = "/home/willian/study-agent/data/biblioteca/"
CSS = re.compile(r"^\s*[\.\#]?\w[\w\-\s\.\:\,\#\[\]\=\(\)\"]*\s*\{.*\}\s*$")

for o in OBRAS:
    p = BASE + o
    if not os.path.exists(p):
        print("FALTA:", o)
        continue
    txt = open(p, encoding="utf-8", errors="ignore").read()
    lines = txt.split("\n")
    kept = [l for l in lines if not CSS.match(l) and "{" not in l or len(l.split()) > 12]
    kept = [l for l in kept if not re.match(r"^\s*[\.\#a-zA-Z0-9_\- ]{0,60}\{[^{}]{0,400}\}\s*$", l)]
    body = "\n".join(kept)
    words = len(body.split())
    print(f"{words:9,d} palavras  |  {os.path.basename(o)}")
