#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Converte de /tmp/governo-dl, cataloga na KB e sobe ao Orbit com nome
'Autor - Titulo'. Governo da igreja / presbiterato / diaconato / lideranca biblica."""
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path("/home/willian/study-agent")
BIB = ROOT / "data/biblioteca"
GLOBAL = BIB / "global"
SRC = Path("/tmp/governo-dl")
ORBIT = ROOT / "data/perfil/bibliotecario/biblioteca-orbit"
TMP = Path("/tmp/conv-governo")
TMP.mkdir(exist_ok=True)

HOJE = "2026-11-16"

# (arquivo, titulo, autor, categoria, kb, ano, tags, nota)
ITENS = [
    ("zlib-29752588.epub", "Presbíteros: Pastoreando o povo de Deus como Jesus",
     "Jeramie Rinne", "igreja", "kb-igreja", "2016",
     ["presbiterato", "oficios", "lideranca", "igreja-local", "9marcas"],
     "Série 9Marcas (Editora Fiel). O que o presbítero faz, como é escolhido e como pastoreia — guia curto e prático, linha batista reformada."),
    ("zlib-116408273.epub", "Diáconos: como eles servem e fortalecem a igreja",
     "Matt Smethurst", "igreja", "kb-igreja", "2022",
     ["diaconato", "oficios", "servico", "igreja-local", "9marcas"],
     "Série 9Marcas (Editora Fiel). Base bíblica do diaconato (At 6; 1Tm 3) e a relação diácono-presbítero."),
    ("zlib-22058486.epub", "Encontrando presbíteros e diáconos fiéis",
     "Thabiti Anyabwile", "igreja", "kb-igreja", "2016",
     ["presbiterato", "diaconato", "oficios", "igreja-local"],
     "Como identificar, examinar e ordenar presbíteros e diáconos — critérios de 1Tm 3 e Tt 1 aplicados à vida da igreja local."),
    ("zlib-125780098.epub", "Anciãos e Diáconos Bíblicos",
     "Nehemiah Coxe", "igreja", "kb-igreja", "2025",
     ["presbiterato", "diaconato", "oficios", "puritano", "batista-1689"],
     "Coxe (séc. XVII), tradutor da Confissão Batista de 1689: tratado sobre nomeação, função e qualificações de anciãos e diáconos."),
    ("zlib-22059890.epub", "Presbiterianismo para leigos",
     "Ralph E. Bass Jr.", "igreja", "kb-igreja", "2019",
     ["presbiterianismo", "governo-igreja", "oficios", "introducao"],
     "Introdução acessível ao governo presbiteriano: concílios, presbíteros docentes e regentes, conexão entre igrejas."),
    ("zlib-22055908.epub", "Entendendo a liderança da igreja (Entendendo a Igreja, vol. 6)",
     "Mark Dever", "igreja", "kb-igreja", "2020",
     ["lideranca", "presbiterato", "oficios", "igreja-local"],
     "Dever: autoridade na igreja local é congregacional sob a liderança dos presbíteros — o que é e o que não é liderança bíblica."),
    ("zlib-23115036.epub", "Pastoreando a Igreja de Deus",
     "Phil A. Newton", "pastoral", "kb-pastoral", "s.d.",
     ["pastoreio", "lideranca", "presbiterato", "igreja-local"],
     "Pastoreio prático: pregação, visitação, cuidado das ovelhas e o trabalho do presbitério na igreja local."),
    ("zlib-14243550.epub", "A Prática da Igreja de Deus: a fé e o funcionamento da igreja bíblica",
     "Marcos Granconato", "igreja", "kb-igreja", "2015",
     ["eclesiologia", "igreja-local", "oficios", "batista"],
     "Autor batista: natureza, membros, ofícios, disciplina e culto da igreja local segundo o NT."),
    ("zlib-22060470.epub", "O Cabeça da Igreja",
     "Charles H. Spurgeon", "igreja", "kb-igreja", "2020",
     ["cristo", "eclesiologia", "igreja-local", "classico"],
     "Sermões de Spurgeon sobre Cristo como única cabeça da igreja — contra a usurpação de autoridade eclesiástica."),
    ("zlib-14242121.epub", "A Igreja do Deus Vivo",
     "Raymond D. Campbell", "igreja", "kb-igreja", "2020",
     ["eclesiologia", "igreja-local", "governo-igreja"],
     "Campbell: a igreja como casa do Deus vivo (1Tm 3.15) — ordem, ofícios e governo segundo o NT."),
    ("zlib-14239881.epub", "Nove Marcas de uma Igreja Saudável",
     "Mark Dever", "igreja", "kb-igreja", "2015",
     ["eclesiologia", "igreja-local", "igreja-saudavel", "9marcas"],
     "Dever: pregação expositiva, teologia bíblica, evangelho, conversão, evangelização, membresia, disciplina, discipulado, liderança."),
    ("zlib-22058930.epub", "O que é um Membro de Igreja Saudável?",
     "Thabiti Anyabwile", "igreja", "kb-igreja", "2018",
     ["membresia", "igreja-local", "discipulado", "9marcas"],
     "Série 9Marcas: o que a membresia bíblica exige do membro — e o que a igreja deve a ele."),
    ("zlib-115083741.epub", "De Volta aos Princípios: vivendo o jeito bíblico de ser igreja",
     "Fabrício Freitas", "igreja", "kb-igreja", "2022",
     ["eclesiologia", "igreja-local", "igreja-multiplicadora"],
     "Série Igreja Multiplicadora: princípios neotestamentários de vida e governo da igreja local."),
    ("zlib-12346576.epub", "Liderança de Poder na Igreja",
     "Brian J. Dodd", "igreja", "kb-igreja", "2011",
     ["lideranca", "poder", "autoridade", "igreja-local"],
     "Dodd: crítica ao modelo de liderança por poder/controle na igreja e proposta de liderança kenótica. LER COM DISCERNIMENTO — autor de linha carismática."),
    ("zlib-22059421.epub", "Igreja Viva: expressões que caracterizam a igreja segundo o modelo bíblico",
     "Didaquê Publicações", "igreja", "kb-igreja", "2017",
     ["eclesiologia", "igreja-local", "igreja-viva"],
     "Série Igreja e Missão: marcas de uma igreja viva segundo o NT."),
    ("zlib-104664381.epub", "Como Edificar uma Igreja Saudável: guia prático para liderança intencional",
     "Paul Alexander & Mark Dever", "igreja", "kb-igreja", "s.d.",
     ["lideranca", "igreja-saudavel", "igreja-local", "pratica"],
     "Manual prático da série 9Marcas: como o líder aplica as nove marcas na vida real da igreja local."),
    ("zlib-27852914.pdf", "Pastores e Diáconos Bíblicos",
     "Nehemiah Coxe & John Owen", "igreja", "kb-igreja", "2020",
     ["presbiterato", "diaconato", "oficios", "puritano"],
     "Dois tratados puritanos reunidos: Coxe sobre anciãos e diáconos; Owen sobre o ofício pastoral e o governo da igreja."),
    ("zlib-16750252.epub", "How Jesus Runs the Church (Como Jesus Governa a Igreja)",
     "Guy Prentiss Waters", "igreja", "kb-igreja", "2012",
     ["governo-igreja", "presbiterianismo", "oficios", "eclesiologia"],
     "INGLÊS. Waters (presbiteriano, RTS): o governo presbiteriano demonstrado a partir do NT — presbíteros, concílios, conexão entre igrejas."),
    ("zlib-16733943.epub", "Biblical Eldership (Presbiterato Bíblico)",
     "Alexander Strauch", "igreja", "kb-igreja", "2016",
     ["presbiterato", "oficios", "lideranca", "igreja-local"],
     "INGLÊS. Strauch: a obra de referência sobre pluralidade de presbíteros que pastoreiam (At 20; 1Tm 3; Tt 1; 1Pe 5)."),
]


def slug(t):
    s = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-")[:70]


def converte(arq):
    for f in TMP.glob("*.md"):
        f.unlink()
    r = subprocess.run([sys.executable, str(ORBIT / "epub2md.py"), str(SRC / arq), "--dest", str(TMP)],
                       capture_output=True, text=True, timeout=1800)
    mds = sorted(TMP.glob("*.md"), key=lambda p: p.stat().st_size, reverse=True)
    if not mds:
        return None, ((r.stdout or "") + (r.stderr or ""))[-300:]
    return mds[0], ""


def kb_add(kb, entrada):
    p = GLOBAL / f"{kb}.yaml"
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    raiz = next(v for v in d.values() if isinstance(v, dict) and "materiais" in v)
    lista = raiz["materiais"]
    if not isinstance(lista, list):
        lista = []
        raiz["materiais"] = lista
    caminho = entrada["caminho_md"]
    lista[:] = [m for m in lista if isinstance(m, dict) and m.get("caminho_md") != caminho]
    lista.append(entrada)
    raiz["total_volumes"] = len(lista)
    raiz["atualizado_em"] = "2026-11-16T03:00:00Z"
    p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=4096), encoding="utf-8")
    return len(lista)


feitos, falhas, ja = [], [], []
for arq, titulo, autor, cat, kb, ano, tags, nota in ITENS:
    src = SRC / arq
    if not src.exists():
        falhas.append((arq, "ausente em /tmp/governo-dl"))
        continue
    destino = BIB / cat / f"{slug(titulo)}-{slug(autor.split('&')[0].split(';')[0])}.md"
    if destino.exists():
        ja.append((titulo, str(destino.relative_to(ROOT))))
        continue
    md, err = converte(arq)
    if not md:
        falhas.append((arq, f"conversao: {err}"))
        continue
    txt = md.read_text(encoding="utf-8", errors="ignore")
    if ("Traceback (most recent call last)" in txt) or len(txt) < 12000:
        falhas.append((arq, f"texto suspeito ({len(txt)} chars)"))
        continue
    cab = (f"---\ntitulo: \"{titulo}\"\nautor: \"{autor}\"\nano: \"{ano}\"\n"
           f"idioma: {'English' if 'INGLÊS' in nota else 'Portuguese'}\n"
           f"formato_original: {src.suffix.lstrip('.')}\n"
           f"tags: [{', '.join(tags)}]\nfonte: z-library ({arq}) {HOJE}\n"
           f"tema: governo-da-igreja\nnota: \"{nota}\"\n---\n\n")
    destino.write_text(cab + txt, encoding="utf-8")
    md.unlink()
    total = kb_add(kb, {
        "titulo": titulo, "autor": autor, "ano": ano,
        "idioma": "English" if "INGLÊS" in nota else "Portuguese",
        "formato_original": src.suffix.lstrip("."),
        "caminho_md": str(destino.relative_to(ROOT)),
        "categoria": "livro", "tags": tags, "fonte": f"z-library ({arq}) {HOJE}",
        "nota": nota, "tamanho_md": f"{destino.stat().st_size//1024} KB",
        "linhas_md": txt.count("\n"), "status": "indexado",
    })
    novo_nome = SRC / f"{slug(autor.split('&')[0].split(';')[0].strip())} - {slug(titulo)}{src.suffix}"
    if novo_nome.exists():
        novo_nome.unlink()
    src.rename(novo_nome)
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "orbit-upload.py"),
                        "--file", str(novo_nome),
                        "--autor", f"{autor.split('&')[0].split(';')[0].strip()} - {titulo}"],
                       capture_output=True, text=True, timeout=180)
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    ok = r.returncode == 0
    if ok:
        novo_nome.unlink()
    print(f"[{'ORBIT-OK' if ok else 'ORBIT-FALHOU'}] {titulo} | kb {total} | "
          f"{out.splitlines()[-1][:130] if out else ''}", flush=True)
    feitos.append((titulo, autor, cat, str(destino.relative_to(ROOT)), total, ok))

print("\n=== RESUMO ===", flush=True)
for t, a, c, p, n, ok in feitos:
    print(f"{'✓' if ok else '⚠'} {t} — {a} [{c}] {p} (kb {n})", flush=True)
for t, p in ja:
    print(f"= {t} (ja catalogado: {p})", flush=True)
for arq, motivo in falhas:
    print(f"✗ {arq}: {motivo}", flush=True)
print(f"\nnovos={len(feitos)} ja={len(ja)} falhas={len(falhas)}", flush=True)
