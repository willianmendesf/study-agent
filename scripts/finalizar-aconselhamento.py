#!/usr/bin/env python3
"""Cataloga os 4 livros de aconselhamento baixados em 2026-11-21."""
import re
import unicodedata
from pathlib import Path

import yaml

ROOT = Path("/home/willian/study-agent")
BIB = ROOT / "data" / "biblioteca"
GLOBAL = BIB / "global"
CONV = Path("/tmp/conv-acons")

ITENS = [
    ("zlib-115963170.md", "Aconselhamento segundo o evangelho: como Cristo transforma vidas",
     "Robert W. Kellemen", "aconselhamento", "kb-aconselhamento", "2022", "Portuguese",
     ["aconselhamento-biblico", "metodologia", "evangelho", "estrutura", "portugues"],
     "Kellemen (Cultura Cristã, 2022; orig. Gospel-Centered Counseling, 2014): método de "
     "aconselhamento estruturado no drama da redenção — criação, queda, redenção, restauração. "
     "Traz o modelo em 4 fases com perguntas e roteiro de sessão. É o mais próximo de um "
     "'como fazer do início ao fim' em português."),
    ("zlib-115103674.md", "O aconselhamento bíblico depois de Jay Adams",
     "Heath Lambert", "aconselhamento", "kb-aconselhamento", "2022", "Portuguese",
     ["aconselhamento-biblico", "metodologia", "historia", "movimento", "portugues"],
     "Lambert (Cultura Cristã, 2022; orig. The Biblical Counseling Movement after Adams, 2011): "
     "mapa do movimento noutético — o que Adams acertou, o que a geração seguinte corrigiu "
     "(sofrimento × pecado, motivação do coração, uso da Escritura). Fundamental para escolher "
     "com consciência o modelo que se vai seguir."),
    ("zlib-116246153.md", "Aconselhamento a partir da cruz: conectando pessoas ao poder curador do amor de Cristo",
     "Elyse M. Fitzpatrick; Dennis E. Johnson", "aconselhamento", "kb-aconselhamento", "2018", "Portuguese",
     ["aconselhamento-biblico", "metodologia", "evangelho", "estudos-de-caso", "portugues"],
     "Fitzpatrick & Johnson (Vida Nova, 2018): aconselhamento que parte do evangelho aplicado ao "
     "coração. Traz estudos de caso reais e a sequência prática de como conduzir a conversa — "
     "identificar ídolos, aplicar a cruz, propor mudança."),
    ("zlib-116246188.md", "Como as pessoas mudam: a mudança centrada no evangelho",
     "Timothy S. Lane; Paul David Tripp", "aconselhamento", "kb-aconselhamento", "2019", "Portuguese",
     ["aconselhamento-biblico", "metodologia", "mudanca", "discipulado", "portugues"],
     "Lane & Tripp (Cultura Cristã, 2019; orig. How People Change, 2006): o modelo dos 3 árvores "
     "(cruz, fruto, raiz) — calor + espinho + cruz + fruto. É o mapa de processo usado pela CCEF "
     "para acompanhar alguém da identificação do problema à mudança efetiva."),
    ("zlib-22058123.md", "Aconselhando uns aos outros: oito maneiras de cultivar relacionamentos saudáveis de cuidado",
     "Edward T. Welch", "aconselhamento", "kb-aconselhamento", "2019", "Portuguese",
     ["aconselhamento-biblico", "igreja-local", "metodologia", "cuidado-mutuo", "portugues"],
     "Welch (Cultura Cristã; orig. Caring for One Another, 2018): oito lições curtas para "
     "treinar a igreja a aconselhar — o formato de currículo pronto (lição + perguntas de "
     "discussão) que dá para rodar em grupo. É o passo 0 da estrutura: criar cultura de "
     "aconselhamento antes de abrir a agenda de atendimentos."),
]


def slug(t):
    s = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-")[:70]


def kb_add(kb, entrada):
    p = GLOBAL / f"{kb}.yaml"
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    raiz = next(v for v in d.values() if isinstance(v, dict) and "materiais" in v)
    lista = raiz["materiais"]
    caminho = entrada["caminho_md"]
    lista[:] = [m for m in lista if m.get("caminho_md") != caminho]
    lista.append(entrada)
    raiz["total_volumes"] = len(lista)
    raiz["atualizado_em"] = "2026-11-21T12:00:00Z"
    p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=4096),
                 encoding="utf-8")
    return len(lista)


feitos, falhas = [], []
for arq, titulo, autor, cat, kb, ano, idioma, tags, nota in ITENS:
    src = CONV / arq
    if not src.exists():
        falhas.append((arq, "ausente"))
        continue
    txt = src.read_text(encoding="utf-8", errors="ignore")
    if "Traceback (most recent call last)" in txt:
        falhas.append((arq, "texto com traceback"))
        continue
    if len(txt) < 12000:
        falhas.append((arq, f"texto curto ({len(txt)} chars)"))
        continue
    destino = BIB / cat / f"{slug(titulo)}-{slug(autor.split(';')[0])}.md"
    cab = (f"---\ntitulo: \"{titulo}\"\nautor: \"{autor}\"\nano: \"{ano}\"\n"
           f"idioma: {idioma}\nformato_original: {arq.rsplit('.', 1)[1]}\n"
           f"tags: [{', '.join(tags)}]\n"
           f"fonte: z-library ({arq.replace('.md', '')}) 2026-11-21\n"
           f"tema: aconselhamento biblico\nnota: \"{nota}\"\n---\n\n")
    destino.write_text(cab + txt, encoding="utf-8")
    total = kb_add(kb, {
        "titulo": titulo, "autor": autor, "ano": ano, "idioma": idioma,
        "formato_original": arq.rsplit(".", 1)[1],
        "caminho_md": str(destino.relative_to(ROOT)),
        "categoria": "livro", "tags": tags,
        "fonte": f"z-library ({arq.replace('.md', '')}) 2026-11-21",
        "nota": nota, "tamanho_md": f"{destino.stat().st_size // 1024} KB",
        "linhas_md": txt.count("\n"), "status": "indexado",
    })
    feitos.append((titulo, autor, cat, str(destino.relative_to(ROOT)), total))

print("=== CATALOGADOS ===")
for t, a, c, p, n in feitos:
    print(f"OK {t} — {a} [{c}] {p} (kb {n})")
print("\n=== FALHAS ===")
for arq, motivo in falhas:
    print(f"X {arq}: {motivo}")
print(f"\ncatalogados={len(feitos)} falhas={len(falhas)}")
