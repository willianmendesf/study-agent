#!/usr/bin/env python3
"""Cataloga os livros de JEJUM baixados em 2026-11-14.

Fluxo por item: .md/.txt ja convertido em /tmp/conv-jejum -> validar ->
frontmatter -> data/biblioteca/<categoria>/ -> KB.
O upload ao BookOrbit e feito depois, em lote, por orbit-upload-lote.py.
"""
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path("/home/willian/study-agent")
BIB = ROOT / "data/biblioteca"
GLOBAL = BIB / "global"
CONV = Path("/tmp/conv-jejum")

# (arquivo_convertido, titulo, autor, categoria, kb, ano, idioma, tags, nota)
ITENS = [
    ("zlib-23047016.md", "A cultura do jejum", "Luciano Subirá", "vida-crista",
     "kb-vida-crista", "2022", "Portuguese",
     ["jejum", "disciplinas-espirituais", "intimidade-com-deus", "contemporaneo"],
     "Subirá (Hagnos, 2022): o jejum como cultura e disciplina na igreja brasileira contemporânea, "
     "não como evento isolado. Perspectiva pentecostal/assembleiana."),
    ("zlib-23348082.txt", "Manual Bíblico do Jejum", "JB Carvalho", "vida-crista",
     "kb-vida-crista", "2020", "Portuguese",
     ["jejum", "manual", "pratica", "biblia"],
     "JB Carvalho (Chara Editora, 2020): manual prático e bíblico do jejum — tipos, duração, "
     "quebrantamento, como quebrar o jejum. Endosso de Lucinho Barreto."),
    ("zlib-11832572.md", "Práticas de Jejum", "Monsenhor Jonas Abib", "vida-crista",
     "kb-vida-crista", "2014", "Portuguese",
     ["jejum", "pratica", "catolico", "livreto"],
     "Abib (Canção Nova, 2014): livreto prático sobre quatro modalidades de jejum. "
     "Teologia católico-carismática — usar pela prática, não como dogmática."),
    ("zlib-21239311.md", "Em Defesa do Jejum", "Danilo Balu", "vida-crista",
     "kb-vida-crista", "2022", "Portuguese",
     ["jejum", "saude", "nutricao", "contemporaneo"],
     "Balu (Clube de Autores, 2022): defesa do jejum pela via da nutrição e da fisiologia "
     "(low-carb, hormese, calorias). NÃO é livro teológico — cita a Bíblia só de passagem. "
     "Serve para a parte física/prática do jejum."),
    ("zlib-5710082.txt", "O Saltério: um livro de orações — 40 dias de Jejum e Oração",
     "Walmir Vargas", "vida-crista", "kb-vida-crista", "2014", "Portuguese",
     ["jejum", "oracao", "salmos", "devocional", "40-dias"],
     "Igreja Batista da Liberdade (2014): 40 devocionais de uma campanha de jejum e oração, "
     "todas extraídas dos Salmos. Modelo pronto de campanha de 40 dias."),
    ("zlib-29049500.md", "Fome por Deus", "John Piper", "vida-crista",
     "kb-vida-crista", "2013", "Portuguese",
     ["jejum", "oracao", "piedade", "reformado", "classico"],
     "Piper (A Hunger for God, 1997; Cultura Cristã 2006, 2ª ed. 2013): o jejum como fome "
     "por Deus — jejum cristão contra o jejum meramente utilitário. Autor reformado batista."),
    ("zlib-16781774.md", "God's Chosen Fast: A Spiritual Guide to Fasting",
     "Arthur Wallis", "vida-crista", "kb-vida-crista", "1993", "English",
     ["jejum", "guia-espiritual", "classico", "ingles"],
     "Wallis (God's Chosen Fast, 1968; CLC 1993): o clássico protestante sobre jejum — "
     "jejum normal, absoluto e parcial; jejuns regulares e públicos; aspectos físicos. "
     "EM INGLÊS."),
    ("zlib-5894207.md", "Fasting for Spiritual Breakthrough: A Guide to Nine Biblical Fasts",
     "Elmer L. Towns", "vida-crista", "kb-vida-crista", "2017", "English",
     ["jejum", "guia", "nove-jejuns", "ingles"],
     "Towns (Bethany House, ed. rev. 2017): os nove jejuns bíblicos (discípulo, Ezra, Ester, "
     "Daniel, Elias, Samuel, Davi, João Batista, Paulo) como método. EM INGLÊS."),
    ("zlib-12343568.md", "A Disciplina Espiritual e as Nossas Atividades",
     "Paul Washer", "vida-crista", "kb-vida-crista", "2016", "Portuguese",
     ["disciplinas-espirituais", "oracao", "devocional", "reformado"],
     "Washer (HeartCry, trad. 2016): transcrição de sermão sobre a disciplina devocional "
     "diária — tempo a sós com Deus. NÃO trata especificamente de jejum; entra como "
     "complemento das disciplinas espirituais."),
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
    raiz["atualizado_em"] = "2026-11-14T21:30:00Z"
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
           f"tags: [{', '.join(tags)}]\nfonte: z-library ({arq.replace('.md', '').replace('.txt', '')}) 2026-11-14\n"
           f"tema: jejum\nnota: \"{nota}\"\n---\n\n")
    destino.write_text(cab + txt, encoding="utf-8")
    total = kb_add(kb, {
        "titulo": titulo, "autor": autor, "ano": ano, "idioma": idioma,
        "formato_original": arq.rsplit(".", 1)[1],
        "caminho_md": str(destino.relative_to(ROOT)),
        "categoria": "livro", "tags": tags,
        "fonte": f"z-library ({arq.replace('.md', '').replace('.txt', '')}) 2026-11-14",
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
