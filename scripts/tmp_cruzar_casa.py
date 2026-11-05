#!/usr/bin/env python3
"""Cruza a lista de livros do William (58 titulos) com o acervo do Study-Agent.

Responde: o que ele JA TEM em casa e o que o acervo do agente tem.
Detecta equivalencias por titulo/autor (normalizado, tokens).
"""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
BIB = ROOT / "data" / "biblioteca"

# lista enviada pelo William (ID, Titulo, Autor)
CASA = [
    (1, "Quando o Espiritual Domina", "Simone de Beauvoir"),
    (2, "Terra dos Homens", "Antoine de Saint-Exupéry"),
    (3, "A Escravidão Na História", "Adam Gurowski"),
    (4, "Babbitt", "Sinclair Lewis"),
    (5, "O Sol Também Se Levanta", "Ernest Hemingway"),
    (6, "Ivanhoé", "Walter Scott"),
    (7, "No Caminho de Swann", "Marcel Proust"),
    (8, "Decamerão", "Giovanni Boccaccio"),
    (9, "Contos", "Voltaire"),
    (10, "Odisséia", "Homero"),
    (11, "Ilusões Perdidas", "Honoré de Balzac"),
    (12, "Eneida", "Virgílio"),
    (13, "Lord Jim", "Joseph Conrad"),
    (14, "Dom Quixote", "Miguel de Cervantes"),
    (15, "A Consciência de Zeno", "Italo Svevo"),
    (16, "Os Amores", "Bocage"),
    (17, "As Aventuras do Sr. Pickwick", "Charles Dickens"),
    (18, "1919", "John dos Passos"),
    (19, "Germinal", "Émile Zola"),
    (20, "A Divina Comédia", "Dante Alighieri"),
    (21, "Cyrano de Bergerac", "Edmond Rostand"),
    (22, "Nostradamus: O Segredo das Centúrias", "Pellos C. Plavgo"),
    (23, "Suave É a Noite", "F. Scott Fitzgerald"),
    (24, "As Vinhas da Ira", "John Steinbeck"),
    (25, "Madame Bovary", "Gustave Flaubert"),
    (26, "Lady Barberina / A Outra Volta do Parafuso", "Henry James"),
    (27, "O Morro dos Ventos Uivantes", "Emily Brontë"),
    (28, "O Vermelho e o Negro", "Stendhal"),
    (29, "As Flores do Mal", "Charles Baudelaire"),
    (30, "Oliver Twist", "Charles Dickens"),
    (31, "Idade da Razão", "Jean-Paul Sartre"),
    (32, "O Retrato de Dorian Gray", "Oscar Wilde"),
    (33, "Tônio Kroeger / A Morte em Veneza", "Thomas Mann"),
    (34, "Mulheres Apaixonadas", "D. H. Lawrence"),
    (35, "Tom Jones", "Henry Fielding"),
    (36, "As Relações Perigosas", "Choderlos de Laclos"),
    (37, "Fausto / Werther", "J. W. Goethe"),
    (38, "O Processo", "Franz Kafka"),
    (39, "Longa Jornada Noite Adentro", "Eugene O'Neill"),
    (40, "Histórias Extraordinárias", "Edgar Allan Poe"),
    (41, "Novelas Exemplares", "Miguel de Cervantes"),
    (42, "A Casa das Sete Torres", "Nathaniel Hawthorne"),
    (43, "Viagens de Gulliver", "Jonathan Swift"),
    (44, "Santuário", "William Faulkner"),
    (45, "O Falecido Mattia Pascal / Seis Personagens à Procura de um Autor", "Luigi Pirandello"),
    (46, "Almas Mortas", "Nikolai Gógol"),
    (47, "Moll Flanders", "Daniel Defoe"),
    (48, "Tartufo / Escola de Mulheres / O Burguês Fidalgo", "Molière"),
    (49, "Estado de Sítio / O Estrangeiro", "Albert Camus"),
    (50, "Pequenos Burgueses / Mãe", "Maxim Gorki"),
    (51, "Casa de Bonecas", "Henrik Ibsen"),
    (52, "As Três Irmãs / Contos", "Anton Tchekhov"),
    (53, "Maria Stuart", "Friedrich Schiller"),
    (54, "A Religiosa", "Denis Diderot"),
    (55, "Os Trabalhadores do Mar", "Victor Hugo"),
    (56, "Obras de Eça de Queiroz (Volume I)", "Eça de Queiroz"),
    (57, "Obras de Eça de Queiroz (Volume II)", "Eça de Queiroz"),
    (58, "Obras de Eça de Queiroz (Volume III)", "Eça de Queiroz"),
]

STOP = {"o", "a", "os", "as", "de", "do", "da", "dos", "das", "e", "em", "no", "na",
        "um", "uma", "para", "com", "que", "se", "por", "ao", "à", "the", "of", "and"}


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c)).lower()


def toks(s):
    return {t for t in re.findall(r"[a-z0-9]+", sem_acento(s)) if t not in STOP and len(t) > 2}


# ---- indice do acervo ----
acervo = []
for f in BIB.rglob("*.md"):
    if "_incoming" in f.parts or "_extracted" in f.parts:
        continue
    try:
        txt = f.read_text(encoding="utf-8", errors="ignore")[:2500]
    except Exception:
        continue
    titulo = ""
    autor = ""
    m = re.search(r'^titulo:\s*["\']?(.*?)["\']?\s*$', txt, re.M)
    if m:
        titulo = m.group(1)
    m = re.search(r'^autor:\s*["\']?(.*?)["\']?\s*$', txt, re.M)
    if m:
        autor = m.group(1)
    if not titulo:
        titulo = f.stem
    acervo.append({
        "path": str(f.relative_to(ROOT)),
        "titulo": titulo,
        "autor": autor,
        "t_toks": toks(titulo),
        "a_toks": toks(autor),
        "stem_toks": toks(f.stem),
    })

print(f"ACERVO: {len(acervo)} .md indexados\n" + "=" * 78)

# equivalencias conhecidas: titulo PT -> (acervo em ingles, trad PT do titulo)
EQUIV = {
    "A Consciência de Zeno": "A Consciência de Zeno (Svevo) — PT do original",
    "O Morro dos Ventos Uivantes": "Wuthering Heights (E. Brontë) — PT do original",
    "Madame Bovary": "Madame Bovary (Flaubert) — PT do original",
    "A Divina Comédia": "Divine Comedy (Dante) — PT do original",
    "Dom Quixote": "Dom Quixote (Cervantes) — PT-BR no acervo",
    "Almas Mortas": "Almas Mortas (Gogol) — PT do original",
    "Germinal": "Germinal (Zola) — PT do original",
    "O Vermelho e o Negro": "O Vermelho e o Negro (Stendhal) — PT do original",
    "No Caminho de Swann": "Em Busca do Tempo Perdido I (Proust) — PT do original",
    "Suave É a Noite": "Suave É a Noite (Fitzgerald) — PT do original",
    "O Retrato de Dorian Gray": "O Retrato de Dorian Gray (Wilde) — PT do original",
    "O Processo": "O Processo (Kafka) — PT do original",
    "As Vinhas da Ira": "As Vinhas da Ira (Steinbeck) — PT do original",
    "O Sol Também Se Levanta": "O Sol Também Se Levanta (Hemingway) — PT do original",
    "Terra dos Homens": "Terra dos Homens (Saint-Exupéry) — PT do original",
    "Histórias Extraordinárias": "Contos de Poe — PT do original",
    "Os Trabalhadores do Mar": "Os Trabalhadores do Mar (Hugo) — PT do original",
    "Ivanhoé": "Ivanhoé (W. Scott) — PT do original",
    "Odisséia": "A Odisséia (Homero) — PT do original",
    "Eneida": "A Eneida (Virgílio) — PT do original",
    "Decamerão": "O Decamerão (Boccaccio) — PT do original",
    "Viagens de Gulliver": "Viagens de Gulliver (Swift) — PT do original",
    "O Falecido Mattia Pascal": "O Falecido Mattia Pascal (Pirandello) — PT do original",
    "Longa Jornada Noite Adentro": "Longa Jornada Noite Adentro (O'Neill) — PT do original",
    "A Religiosa": "A Religiosa (Diderot) — PT do original",
    "Moll Flanders": "Moll Flanders (Defoe) — PT do original",
    "Lord Jim": "Lord Jim (Conrad) — PT do original",
    "Fausto / Werther": "Fausto (Goethe) — PT do original",
    "Ilusões Perdidas": "Ilusões Perdidas (Balzac) — PT do original",
    "A Casa das Sete Torres": "A Casa das Sete Torres (Hawthorne) — PT do original",
    "Santuário": "Santuário (Faulkner) — PT do original",
    "Babbitt": "Babbitt (S. Lewis) — PT do original",
    "As Aventuras do Sr. Pickwick": "Oliver Twist / Pickwick (Dickens) — PT do original",
    "Tartufo / Escola de Mulheres / O Burguês Fidalgo": "Molière — PT do original",
    "Casa de Bonecas": "Casa de Bonecas (Ibsen) — PT do original",
    "Maria Stuart": "Maria Stuart (Schiller) — PT do original",
    "Cyrano de Bergerac": "Cyrano de Bergerac (Rostand) — PT do original",
    "As Relações Perigosas": "As Relações Perigosas (Laclos) — PT do original",
    "Mulheres Apaixonadas": "Mulheres Apaixonadas (D. H. Lawrence) — PT do original",
    "Tônio Kroeger / A Morte em Veneza": "Tônio Kroeger / A Morte em Veneza (Mann) — PT do original",
    "Estado de Sítio / O Estrangeiro": "O Estrangeiro (Camus) — PT do original",
    "Pequenos Burgueses / Mãe": "Pequenos Burgueses / Mãe (Gorki) — PT do original",
    "As Três Irmãs / Contos": "Contos de Tchekhov — PT do original",
    "Contos": "Contos de Voltaire — PT do original",
    "1919": "1919 (John dos Passos) — PT do original",
    "A Escravidão Na História": "A Escravidão na História (Gurowski) — PT do original",
    "Nostradamus: O Segredo das Centúrias": "Nostradamus (Plavgo) — PT do original",
    "Idade da Razão": "A Idade da Razão (Sartre) — PT do original",
    "Quando o Espiritual Domina": "O Segundo Sexo /、修理 (Beauvoir) — PT do original",
    "As Flores do Mal": "As Flores do Mal (Baudelaire) — PT do original",
    "Tom Jones": "Tom Jones (Fielding) — PT do original",
    "As Três Irmãs": "Três Irmãs (Tchekhov) — PT do original",
    "Novelas Exemplares": "Novelas Exemplares (Cervantes) — PT do original",
    "Obras de Eça de Queiroz (Volume I)": "Eça de Queiroz vol. I — PT do original",
    "Obras de Eça de Queiroz (Volume II)": "Eça de Queiroz vol. II — PT do original",
    "Obras de Eça de Queiroz (Volume III)": "Eça de Queiroz vol. III — PT do original",
}

rows = []
for i, tit, aut in CASA:
    tt = toks(tit)
    achados = []
    for a in acervo:
        inter = tt & (a["t_toks"] | a["stem_toks"])
        if not inter:
            continue
        # exige cobertura boa do titulo OU sobrenome do autor batendo
        cob = len(inter) / max(1, len(tt))
        sob = ""
        if aut:
            pt = toks(aut)
            ab = {t for t in a["a_toks"] | a["stem_toks"]}
            sob = ",".join(sorted(pt & ab))
        if cob >= 0.6 or (len(tt) >= 2 and sob and len(inter) >= 2):
            achados.append((round(cob, 2), a["path"], a["titulo"], a["autor"], sob))
    achados.sort(reverse=True)
    rows.append((i, tit, aut, achados))

print("\n### TITULOS DO WILLIAM QUE JA EXISTEM NO ACERVO DO AGENTE\n")
n_acervo = 0
for i, tit, aut, ach in rows:
    if not ach:
        continue
    n_acervo += 1
    cob, p, t, a, sob = ach[0]
    print(f"[{i:02d}] {tit}  ({aut})")
    print(f"     -> {t} | {a} | cobertura={cob} | auto_bate={sob or '-'}")
    print(f"        {p}")
print(f"\n{n_acervo} de {len(CASA)} titulos do William tem correspondencia no acervo.")

print("\n\n### TITULOS DO WILLIAM QUE NAO ESTAO NO ACERVO (ou sem correspondencia forte)\n")
for i, tit, aut, ach in rows:
    if ach:
        continue
    eq = EQUIV.get(tit, "")
    print(f"[{i:02d}] {tit} — {aut}   {('| ' + eq) if eq else ''}")

print("\n\n### TITULOS DO WILLAIN QUE JA ESTAO NO ACERVO (traducoes PT de urgencia)\n")
for tit, nota in EQUIV.items():
    tt = toks(tit)
    ach = []
    for a in acervo:
        inter = tt & (a["t_toks"] | a["stem_toks"])
        if inter and len(inter) / max(1, len(tt)) >= 0.6:
            ach.append(a)
    if ach:
        for a in ach[:1]:
            print(f"  {tit:45s} -> {a['titulo'][:45]:45s} [{a['autor'][:22]}]")
