#!/usr/bin/env python3
"""Cataloga o John Eckhardt (PDF escaneado, OCR) — livro de JEJUM."""
import re
import unicodedata
from pathlib import Path

import yaml

ROOT = Path("/home/willian/study-agent")
BIB = ROOT / "data/biblioteca"
GLOBAL = BIB / "global"

SRC = Path("/tmp/conv-jejum/eckhardt-ocr.txt")
TITULO = "Jejum: como encontrar respostas e se aproximar de Deus"
AUTOR = "John Eckhardt"
CAT = "vida-crista"
KB = "kb-vida-crista"
ANO = "2017"
TAGS = ["jejum", "oracao", "libertacao", "intercessao", "carismatico"]
NOTA = ("Eckhardt (Jejum, Renova 2017; orig. Fasting for Breakthrough and Deliverance): "
        "jejum como arma de libertação — jejum e orações de quebra de fortalezas. "
        "Teologia carismática/pentecostal — ler com discernimento. "
        "Extraído por OCR de PDF escaneado (121 pág.).")


def slug(t):
    s = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-")[:70]


txt = SRC.read_text(encoding="utf-8", errors="ignore")
assert "Traceback (most recent call last)" not in txt, "texto com traceback"
assert len(txt) > 12000, f"texto curto: {len(txt)}"

destino = BIB / CAT / f"{slug(TITULO)}-{slug(AUTOR)}.md"
cab = (f"---\ntitulo: \"{TITULO}\"\nautor: \"{AUTOR}\"\nano: \"{ANO}\"\n"
       f"idioma: Portuguese\nformato_original: pdf (OCR)\n"
       f"tags: [{', '.join(TAGS)}]\nfonte: z-library (zlib-18094941.pdf) 2026-11-14\n"
       f"tema: jejum\nnota: \"{NOTA}\"\n---\n\n")
destino.write_text(cab + txt, encoding="utf-8")

p = GLOBAL / f"{KB}.yaml"
d = yaml.safe_load(p.read_text(encoding="utf-8"))
raiz = next(v for v in d.values() if isinstance(v, dict) and "materiais" in v)
lista = raiz["materiais"]
caminho = str(destino.relative_to(ROOT))
lista[:] = [m for m in lista if m.get("caminho_md") != caminho]
lista.append({
    "titulo": TITULO, "autor": AUTOR, "ano": ANO, "idioma": "Portuguese",
    "formato_original": "pdf", "caminho_md": caminho, "categoria": "livro",
    "tags": TAGS, "fonte": "z-library (zlib-18094941.pdf) 2026-11-14",
    "nota": NOTA, "tamanho_md": f"{destino.stat().st_size // 1024} KB",
    "linhas_md": txt.count("\n"), "status": "indexado",
})
raiz["total_volumes"] = len(lista)
raiz["atualizado_em"] = "2026-11-14T21:50:00Z"
p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=4096), encoding="utf-8")
print(f"OK {TITULO} -> {caminho} (kb {len(lista)})")
