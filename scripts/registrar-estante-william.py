#!/usr/bin/env python3
"""Registra a lista de 58 livros de casa do William como documento canonico.

Cria:
  data/biblioteca/literatura/estante-william-58-livros.md  (ficha legivel + tabela)
  data/perfil/bibliotecario/estante-william.yaml            (dados estruturados)
"""
import unicodedata
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
OUT_MD = ROOT / "data" / "biblioteca" / "literatura" / "estante-william-58-livros.md"
OUT_YAML = ROOT / "data" / "perfil" / "bibliotecario" / "estante-william.yaml"

CASA = [
    (1, "Quando o Espiritual Domina", "Simone de Beauvoir", "Coleção Grandes Escritoras"),
    (2, "Terra dos Homens", "Antoine de Saint-Exupéry", "Coleção Clássicos Para Todos"),
    (3, "A Escravidão Na História", "Adam Gurowski", ""),
    (4, "Babbitt", "Sinclair Lewis", ""),
    (5, "O Sol Também Se Levanta", "Ernest Hemingway", "Edição encadernada (capa verde/dourada)"),
    (6, "Ivanhoé", "Walter Scott", ""),
    (7, "No Caminho de Swann", "Marcel Proust", ""),
    (8, "Decamerão", "Giovanni Boccaccio", ""),
    (9, "Contos", "Voltaire", ""),
    (10, "Odisséia", "Homero", ""),
    (11, "Ilusões Perdidas", "Honoré de Balzac", ""),
    (12, "Eneida", "Virgílio", ""),
    (13, "Lord Jim", "Joseph Conrad", ""),
    (14, "Dom Quixote", "Miguel de Cervantes", ""),
    (15, "A Consciência de Zeno", "Italo Svevo", ""),
    (16, "Os Amores", "Bocage", ""),
    (17, "As Aventuras do Sr. Pickwick", "Charles Dickens", ""),
    (18, "1919", "John dos Passos", ""),
    (19, "Germinal", "Émile Zola", ""),
    (20, "A Divina Comédia", "Dante Alighieri", ""),
    (21, "Cyrano de Bergerac", "Edmond Rostand", ""),
    (22, "Nostradamus: O Segredo das Centúrias", "Pellos C. Plavgo", ""),
    (23, "Suave É a Noite", "F. Scott Fitzgerald", ""),
    (24, "As Vinhas da Ira", "John Steinbeck", ""),
    (25, "Madame Bovary", "Gustave Flaubert", ""),
    (26, "Lady Barberina / A Outra Volta do Parafuso", "Henry James", "Volume composto com duas novelas"),
    (27, "O Morro dos Ventos Uivantes", "Emily Brontë", ""),
    (28, "O Vermelho e o Negro", "Stendhal", ""),
    (29, "As Flores do Mal", "Charles Baudelaire", ""),
    (30, "Oliver Twist", "Charles Dickens", ""),
    (31, "Idade da Razão", "Jean-Paul Sartre", "Editora Abril"),
    (32, "O Retrato de Dorian Gray", "Oscar Wilde", ""),
    (33, "Tônio Kroeger / A Morte em Veneza", "Thomas Mann", "Volume composto"),
    (34, "Mulheres Apaixonadas", "D. H. Lawrence", ""),
    (35, "Tom Jones", "Henry Fielding", ""),
    (36, "As Relações Perigosas", "Choderlos de Laclos", ""),
    (37, "Fausto / Werther", "J. W. Goethe", "Volume composto"),
    (38, "O Processo", "Franz Kafka", ""),
    (39, "Longa Jornada Noite Adentro", "Eugene O'Neill", ""),
    (40, "Histórias Extraordinárias", "Edgar Allan Poe", ""),
    (41, "Novelas Exemplares", "Miguel de Cervantes", ""),
    (42, "A Casa das Sete Torres", "Nathaniel Hawthorne", ""),
    (43, "Viagens de Gulliver", "Jonathan Swift", ""),
    (44, "Santuário", "William Faulkner", ""),
    (45, "O Falecido Mattia Pascal / Seis Personagens à Procura de um Autor", "Luigi Pirandello", "Volume composto (romance + peça)"),
    (46, "Almas Mortas", "Nikolai Gógol", ""),
    (47, "Moll Flanders", "Daniel Defoe", ""),
    (48, "Tartufo / Escola de Mulheres / O Burguês Fidalgo", "Molière", "Coletânea de peças teatrais"),
    (49, "Estado de Sítio / O Estrangeiro", "Albert Camus", "Volume composto"),
    (50, "Pequenos Burgueses / Mãe", "Maxim Gorki", "Volume composto"),
    (51, "Casa de Bonecas", "Henrik Ibsen", ""),
    (52, "As Três Irmãs / Contos", "Anton Tchekhov", "Volume composto"),
    (53, "Maria Stuart", "Friedrich Schiller", ""),
    (54, "A Religiosa", "Denis Diderot", ""),
    (55, "Os Trabalhadores do Mar", "Victor Hugo", ""),
    (56, "Obras de Eça de Queiroz (Volume I)", "Eça de Queiroz", "Obras completas / antologia"),
    (57, "Obras de Eça de Queiroz (Volume II)", "Eça de Queiroz", "Obras completas / antologia"),
    (58, "Obras de Eça de Queiroz (Volume III)", "Eça de Queiroz", "Contém: A Capital, O Conde de Abranhos, Alves & C.ª, etc."),
]

# agrupamento por eixo (para a rampa)
EIXO = {
    "realismo-frances": [11, 19, 25, 28, 54, 55, 8, 35, 36, 48],
    "romantismo-e-seguintes": [6, 12, 21, 43, 52, 53, 51, 39, 27, 42, 44, 26],
    "realismo-ingles": [14, 17, 30, 41, 47, 13, 5, 24, 23, 32, 31, 7],
    "modernismo-e-experimental": [15, 33, 29, 34, 50, 45, 49, 3, 18, 1, 22],
    "antigos-e-classicos": [10, 20, 2, 37, 4, 38, 16, 9, 40],
}

NAMES = {
    "realismo-frances": "Realismo francês e连环",
    "romantismo-e-seguintes": "Romantismo, gótico e finais do XIX",
    "realismo-ingles": "Realismo inglês e locked-room",
    "modernismo-e-experimental": "Modernismo, modernidade e experimental",
    "antigos-e-classicos": "Antigos, clássicos e poesia",
}
NAMES = {
    "realismo-frances": "Realismo francês e Escola de Paris",
    "romantismo-e-seguintes": "Romantismo, gótico e finais do XIX",
    "realismo-ingles": "Realismo inglês e locked-room",
    "modernismo-e-experimental": "Modernismo, modernidade e experimental",
    "antigos-e-classicos": "Antigos, clássicos e poesia",
}

GRUPOS = {
    "realismo-frances": ("Realismo francês e Escola de Paris",
                         "Flaubert, Zola, Balzac, Stendhal, Diderot, Hugo, Boccaccio, Fielding, Laclos, Molière"),
    "romantismo-e-seguintes": ("Romantismo, gótico e finais do XIX",
                                "Scott, Virgílio, Rostand, Swift, Tchekhov, Schiller, Ibsen, O'Neill, Brontë, Hawthorne, Faulkner, James"),
    "realismo-ingles": ("Realismo inglês e locked-room",
                        "Cervantes, Dickens (×3), Defoe, Conrad, Hemingway, Steinbeck, Fitzgerald, Wilde, Sartre, Proust"),
    "modernismo-e-experimental": ("Modernismo, modernidade e experimental",
                                  "Svevo, Mann, Baudelaire, Lawrence, Gorki, Pirandello, Camus, Gurowski, dos Passos, Beauvoir, Plavgo"),
    "antigos-e-classicos": ("Antigos, clássicos e poesia",
                            "Homero, Dante, Saint-Exupéry, Goethe, Sinclair Lewis, Kafka, Bocage, Voltaire, Poe"),
}

linhas = []
linhas.append("""---
titulo: "Estante do William — 58 livros de casa"
autor: "Estante pessoal de William"
tipo: "lista"
tags:
  - literatura
  - canon-literario
  - literatura-mundial
  - leitura-formacao
  - estante-pessoal
data: 2026-11-05
origem: "Lista enviada pelo William via Telegram (CSV + texto)"
---

# Estante do William — 58 livros de casa

Registro da estante pessoal de William, recebida em 2026-11-05. Serve de referência
para: (a) o cruzamento com o acervo do Study-Agent, (b) a ordem de leitura da rampa de
ficção, (c) o plano de aquisição de material que **não** está em casa.

O cruzamento completo está em
`data/estudos/notas/ficcao-rampa-leitura/02-cruzamento-lista-de-casa.md`.

## Resumo

- **58 títulos**, de 1589 (Shakespeare, via Voltaire) a 1976 (Dostoiévski, via Plavgo).
- **54 dos 58** não estão no acervo do Study-Agent (a maioria em português).
- **1** já está no acervo em português: *Dom Quixote*.
- **3** dos clássicos do acervo estão em inglês (Dante, Dostoiévski, Tolstói, Agostinho, Dickens).
- **1 única mulher autora** em 58 títulos: Simone de Beauvoir.
- **Zero ficção cristã** na estante.

## A lista

| # | Título | Autor | Detalhes | Eixo |
|---|---|---|---|---|
""")

eixo_de = {}
for chave, ids in EIXO.items():
    for i in ids:
        eixo_de[i] = chave

for i, tit, aut, det in CASA:
    d = det.replace("|", "\\|") or "—"
    e = eixo_de.get(i, "—")
    linhas.append(f"| {i} | {tit} | {aut} | {d} | {e} |\n")

linhas.append("""
## Agrupamento por eixo de leitura

""")
for chave, (nome, autores) in GRUPOS.items():
    linhas.append(f"### {nome}\n\n*{autores}*\n\n")
    for i in sorted(EIXO[chave]):
        t, a, _, _ = CASA[i - 1]
        linhas.append(f"- **{t}** — {a}\n")
    linhas.append("\n")

OUT_MD.parent.mkdir(parents=True, exist_ok=True)
OUT_MD.write_text("".join(linhas), encoding="utf-8")

# ---- YAML estruturado ----
def esc(s):
    return "'" + s.replace("'", "''") + "'"

y = []
y.append("# Estante pessoal de William — 58 livros (registro canonico)\n")
y.append("data: 2026-11-05\n")
y.append("origem: lista enviada via Telegram\n")
y.append(f"total: {len(CASA)}\n")
y.append("titulo: Estante do William — 58 livros de casa\n")
y.append("tipo: lista\n")
y.append("tags:\n  - literatura\n  - canon-literario\n  - literatura-mundial\n")
y.append("  - leitura-formacao\n  - estante-pessoal\n")
y.append("livros:\n")
for i, tit, aut, det in CASA:
    y.append(f"  - id: {i}\n")
    y.append(f"    titulo: {esc(tit)}\n")
    y.append(f"    autor: {esc(aut)}\n")
    if det:
        y.append(f"    detalhes: {esc(det)}\n")
    y.append(f"    eixo: {esc(eixo_de.get(i, 'nao-classificado'))}\n")
    y.append(f"    no_acervo_study_agent: {'sim' if i == 14 else 'nao'}\n")
y.append("resumo:\n")
y.append(f"  total: {len(CASA)}\n")
y.append("  so_na_estante: 54\n")
y.append("  ja_no_acervo_pt: 1\n")
y.append("  classicos_do_acervo_em_ingles: 6\n")
y.append("  buracos: 'Dostoyevsky, Tolstoi, Austen, autoras Submission'\n")
y.append("  gaps_de_intencao: 'zero ficcao cristiana'\n")

OUT_YAML.parent.mkdir(parents=True, exist_ok=True)
OUT_YAML.write_text("".join(y), encoding="utf-8")

print(f"OK  {OUT_MD.relative_to(ROOT)}  ({OUT_MD.stat().st_size//1024} KB)")
print(f"OK  {OUT_YAML.relative_to(ROOT)}  ({OUT_YAML.stat().st_size//1024} KB)")
