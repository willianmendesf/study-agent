#!/usr/bin/env python3
"""Converte, cataloga e sobe ao BookOrbit os livros de ORACAO baixados em 2026-11-14.

Fluxo por item: CONVERTER -> VALIDAR -> FRONTMATTER -> .md na categoria
                -> KB -> ORBIT (upload do original) -> apagar original local.
"""
import json, re, subprocess, sys, unicodedata
from pathlib import Path

import yaml

ROOT = Path("/home/willian/study-agent")
BIB = ROOT / "data/biblioteca"
GLOBAL = BIB / "global"
INC = BIB / "_incoming"
ORBIT = ROOT / "data/perfil/bibliotecario/biblioteca-orbit"
TMP = Path("/tmp/conv-oracao2")
TMP.mkdir(exist_ok=True)

# (arquivo, titulo, autor, categoria, kb, ano, tags, nota)
ITENS = [
    ("zlib-12346777.epub", "Poder Através da Oração", "E. M. Bounds", "vida-crista",
     "kb-vida-crista", "s.d.", ["oracao", "poder", "clássico", "puritano"],
     "Clássico de Bounds (Power Through Prayer, 1907): o pregador e a vida de oração. Tradução Editora Batista Regular."),
    ("zlib-26731031.epub", "Senhor, Ensina-me a Orar (Escola da Oração)", "Andrew Murray", "vida-crista",
     "kb-vida-crista", "s.d.", ["oracao", "devocional", "escola-da-oracao"],
     "31 dias de meditações sobre a oração, no espírito de Lucas 11.1."),
    ("zlib-72968720.pdf", "Orando a Palavra: Como Orar como a Bíblia nos Ensinou",
     "C. H. Spurgeon; E. M. Bounds; R. A. Torrey", "vida-crista",
     "kb-vida-crista", "s.d.", ["oracao", "biblia", "coletanea", "clássico"],
     "Coletânea de três clássicos sobre oração bíblica: Spurgeon, Bounds e Torrey."),
    ("zlib-21756102.epub", "A Oração de Paulo (Escola da Oração, vol. 1)", "Charles H. Spurgeon",
     "vida-crista", "kb-vida-crista", "1855", ["oracao", "paulo", "sermao", "clássico"],
     "Sermão de Spurgeon (25/03/1855, Exeter Hall) sobre Atos 9.11: 'Pois eis que ele está orando'."),
    ("zlib-22060618.pdf", "A Mortificação do Pecado", "John Owen", "santidade",
     "kb-santidade", "s.d.", ["santidade", "pecado", "puritano", "clássico"],
     "Owen (Of the Mortification of Sin in Believers, 1656): como o crente luta contra o pecado — vida de oração e dependência do Espírito."),
    ("zlib-22109847.pdf", "Um Chamado à Reforma Espiritual", "D. A. Carson", "vida-crista",
     "kb-vida-crista", "s.d.", ["oracao", "avivamento", "reforma", "igreja"],
     "Carson (A Call to Spiritual Reformation): exposição das orações de Paulo como escola de oração."),
    ("zlib-5726737.pdf", "Celebração da Disciplina: O Caminho do Crescimento Espiritual",
     "Richard J. Foster", "vida-crista", "kb-vida-crista", "1983",
     ["disciplinas-espirituais", "oracao", "jejum", "meditacao"],
     "Foster (Celebration of Discipline, 1978): as disciplinas interiores incluem meditação, oração, jejum e estudo."),
    ("zlib-22423480.epub", "Em Busca de Deus", "A. W. Tozer", "vida-crista",
     "kb-vida-crista", "s.d.", ["oracao", "busca-de-deus", "devocional"],
     "Tozer (The Pursuit of God, 1948). ATENÇÃO: extração com OCR de qualidade irregular (texto legível, mas com trocas de letras na folha de rosto)."),
    ("zlib-117111472.epub", "Confissões", "Agostinho de Hipona", "espiritualidade-reformada",
     "kb-espiritualidade-reformada", "s.d.", ["agostinho", "oracao", "clássico", "autobiografia"],
     "As Confissões são, na forma, uma longa oração dirigida a Deus — modelo devocional de introspecção e graça."),
    ("zlib-125574839.epub", "Gerando em Oração", "Amanda Josepetti", "vida-crista",
     "kb-vida-crista", "2026", ["oracao", "intercessao", "contemporaneo"],
     "Editora Vida (2026): vida de oração e intercessão."),
    ("zlib-126852764.epub", "Devocional Quarto de Guerra", "Isabelle S. Alves", "vida-crista",
     "kb-vida-crista", "s.d.", ["oracao", "devocional", "intercessao"],
     "Devocional diário de oração e intercessão."),
    ("zlib-127506646.epub", "A Luta da Oração", "Donald G. Bloesch", "vida-crista",
     "kb-vida-crista", "s.d.", ["oracao", "teologia", "intercessao"],
     "Bloesch (The Struggle of Prayer): teologia bíblica da oração — oração como ação, intercessão e luta."),
    ("zlib-49084043.epub", "O Privilégio da Oração", "Arival Dias Casimiro", "vida-crista",
     "kb-vida-crista", "2024", ["oracao", "presbiteriano", "ipb", "devocional"],
     "Associação Editora Presbiteriana de Pinheiros (2024): desfrutar o privilégio de falar com Deus. Autor presbiteriano (IPB)."),
    ("zlib-123531349.epub", "O Poder da Oração pelo Casamento", "Elizabeth George", "familia-crista",
     "kb-familia-crista", "s.d.", ["oracao", "casamento", "mulheres"],
     "Elizabeth George: oração intercessória pelos capítulos do casamento (marido, filhos, finanças, visão)."),
    ("zlib-116144425.epub", "O Poder Secreto da Oração e do Jejum", "Mahesh Chavda", "vida-crista",
     "kb-vida-crista", "s.d.", ["oracao", "jejum", "intercessao", "avivamento"],
     "Chavda: oração e jejum como liberação do poder da igreja que ora. Teologia carismática — ler com discernimento."),
    ("zlib-21942514.epub", "A Oração", "Santo Afonso de Ligório", "vida-crista",
     "kb-vida-crista", "1757", ["oracao", "classico", "catolico"],
     "Santo Afonso (1696-1787), 'Doutor da Oração': tratado sobre a oração como pedido, súplica e ação de graças. Teologia católica — usar pelo devocional, não como dogmática."),
    ("zlib-117398270.epub", "Bíblia de Estudo Conciso: Oração e Intercessão (Módulo 1)", "Neuza Itioka",
     "vida-crista", "kb-vida-crista", "s.d.", ["oracao", "intercessao", "biblia-de-estudo"],
     "Módulo de estudo bíblico sobre oração e intercessão (material curto, ~24 mil caracteres)."),
    ("zlib-22057740.epub", "Comentário Bíblico Matthew Henry: Salmos a Malaquias",
     "Matthew Henry", "comentarios-biblicos", "kb-comentarios-biblicos", "s.d.",
     ["comentario-biblico", "salmos", "classico", "devocional"],
     "Matthew Henry (1662-1714) sobre o AT, de Salmos a Malaquias. Os Salmos são o livro de oração de Israel — comentário devocional clássico."),
]

IGNORADOS = [
    ("zlib-16758940.epub", "Packer, Puritan Portraits (inglês; sobre puritanos, não sobre oração)"),
    ("zlib-29638874.epub", "Whitney, Disciplinas Espirituales (espanhol; já temos em inglês)"),
    ("zlib-26893499.epub", "Socorro Acioli, Oração para Desaparecer (ficção, não é sobre oração)"),
    ("zlib-19257965.epub", "Joseph Murphy, O Poder da Oração (Novo Pensamento, não cristão)"),
]


def slug(t):
    s = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-")[:70]


def converte(arq):
    for f in TMP.glob("*.md"):
        f.unlink()
    r = subprocess.run([sys.executable, str(ORBIT / "epub2md.py"), str(INC / arq), "--dest", str(TMP)],
                       capture_output=True, text=True, timeout=1200)
    mds = sorted(TMP.glob("*.md"), key=lambda p: p.stat().st_size, reverse=True)
    if not mds:
        return None, ((r.stdout or "") + (r.stderr or ""))[-300:]
    return mds[0], ""


def kb_add(kb, entrada):
    p = GLOBAL / f"{kb}.yaml"
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    raiz = next(v for v in d.values() if isinstance(v, dict) and "materiais" in v)
    lista = raiz["materiais"]
    caminho = entrada["caminho_md"]
    lista[:] = [m for m in lista if m.get("caminho_md") != caminho]
    lista.append(entrada)
    raiz["total_volumes"] = len(lista)
    raiz["atualizado_em"] = "2026-11-14T14:30:00Z"
    p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=4096), encoding="utf-8")
    return len(lista)


feitos, falhas = [], []
for arq, titulo, autor, cat, kb, ano, tags, nota in ITENS:
    src = INC / arq
    if not src.exists():
        falhas.append((arq, "ausente"))
        continue
    md, err = converte(arq)
    if not md:
        falhas.append((arq, f"conversao: {err}"))
        continue
    txt = md.read_text(encoding="utf-8", errors="ignore")
    if ("Traceback (most recent call last)" in txt) or len(txt) < 12000:
        falhas.append((arq, f"texto suspeito ({len(txt)} chars)"))
        continue
    destino = BIB / cat / f"{slug(titulo)}-{slug(autor.split(';')[0])}.md"
    cab = (f"---\ntitulo: \"{titulo}\"\nautor: \"{autor}\"\nano: \"{ano}\"\n"
           f"idioma: Portuguese\nformato_original: {src.suffix.lstrip('.')}\n"
           f"tags: [{', '.join(tags)}]\nfonte: z-library ({arq}) 2026-11-14\n"
           f"tema: oracao\nnota: \"{nota}\"\n---\n\n")
    destino.write_text(cab + txt, encoding="utf-8")
    md.unlink()
    total = kb_add(kb, {
        "titulo": titulo, "autor": autor, "ano": ano, "idioma": "Portuguese",
        "formato_original": src.suffix.lstrip("."), "caminho_md": str(destino.relative_to(ROOT)),
        "categoria": "livro", "tags": tags, "fonte": f"z-library ({arq}) 2026-11-14",
        "nota": nota, "tamanho_md": f"{destino.stat().st_size//1024} KB",
        "linhas_md": txt.count("\n"), "status": "indexado",
    })
    # upload ao BookOrbit com "Autor - Titulo" (o app deriva titulo/autor do nome)
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "orbit-upload.py"),
                        "--file", str(src), "--autor", f"{autor.split(';')[0].strip()} - {titulo}"],
                       capture_output=True, text=True, timeout=180)
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    ok = r.returncode == 0
    print(f"[{'OK' if ok else 'UPLOAD-FALHOU'}] {titulo} | {total} na KB | {out.splitlines()[-1][:140] if out else ''}", flush=True)
    if ok:
        src.unlink()
    feitos.append((titulo, autor, cat, str(destino.relative_to(ROOT)), total, ok))

print("\n=== RESUMO ===", flush=True)
for t, a, c, p, n, ok in feitos:
    print(f"{'✓' if ok else '⚠'} {t} — {a} [{c}] {p} (kb {n})", flush=True)
for arq, motivo in falhas:
    print(f"✗ {arq}: {motivo}", flush=True)
print(f"\nconvertidos+catalogados={len(feitos)} falhas={len(falhas)}", flush=True)
for arq, motivo in IGNORADOS:
    print(f"descartado {arq}: {motivo}", flush=True)
