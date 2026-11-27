#!/usr/bin/env python3
"""Gera o catalogo de aquisicao de ficcao (YAML) a partir de 3 fontes:

  1. `data/perfil/bibliotecario/estante-william.yaml`  -> 49 obras que o William
     TEM em casa e o acervo NAO tem (bloco #182 da lista de aquisicao)
  2. `data/biblioteca/lista-aquisicao.md` blocos #140-#144 -> as obras da RAMPA
     (que o William NAO tem em casa)
  3. uma lista manual de Complementares (ficcao cristiana, degrau 5, PT-BR
     de classicos que so existem em ingles no acervo)

Regras:
  - **Volume composto vira obra separada.** "Lady Barberina / A Outra Volta do
    Parafuso" (E26) sao DUAS novelas de Henry James; comprar a coletanea e
    nao serve. Cada obra entra como item proprio.
  - **Nao-ficcao sai.** "A Escravidao na Historia" (Gurowski, 1826) e'
    historiografia, nao ficcao -> fica fora do catalogo de ficcao.
  - **Eca de Queiroz (E56-E58)** e' digitalizacao da estante fisica, nao download
    -> fica fora (exige scanner).
  - Cada item tem `titulo_en` para o fallback de busca quando o PT nao existe.

Uso: python3 scripts/gerar-catalogo-ficcao.py
Saida: data/perfil/bibliotecario/catalogo-ficcao.yaml
"""
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ESTANTE = ROOT / "data/perfil/bibliotecario/estante-william.yaml"
LISTA = ROOT / "data/biblioteca/lista-aquisicao.md"
OUT = ROOT / "data/perfil/bibliotecario/catalogo-ficcao.yaml"

# ---------------------------------------------------------------------------
# 1. volumes compostos da estante -> cada obra separada
#    (id_estante, titulo separado, autor, subpasta, titulo_en, tags extra)
# ---------------------------------------------------------------------------
COMPOSTOS = {
    26: [("Lady Barberina", "The Way It Came", "ingles"),
         ("A Outra Volta do Parafuso", "The Turn of the Screw", "ingles")],
    33: [("Tônio Kroeger", "Tonio Kroeger", "alemão"),
         ("A Morte em Veneza", "Death in Venice", "alemão")],
    45: [("O Falecido Mattia Pascal", "Il Mattia Pascal", "italiano"),
         ("Seis Personagens à Procura de um Autor", "Sei personaggi in cerca d'autore",
          "italiano")],
    48: [("Tartufo", "Tartuffe", "frances"),
         ("A Escola de Mulheres", "L'École des femmes", "frances"),
         ("O Burguês Fidalgo", "Le Bourgeois gentilhomme", "frances")],
    49: [("Estado de Sítio", "L'État de siège", "frances"),
         ("O Estrangeiro", "L'Étranger", "frances")],
    50: [("Pequenos Burgueses", "Meščane", "russo"),
         ("Mãe", "Mat'", "russo")],
    52: [("As Três Irmãs", "Three Sisters", "russo"),
         ("Contos", "Short Stories", "russo")],
    37: [("Fausto", "Faust", "alemão"),
         ("Werther", "Die Leiden des jungen Werthers", "alemão")],
}

# nao-ficcao / digitalizacao: fora do catalogo de download
EXCLUIR = {3, 56, 57, 58}

# subpasta por eixo da estante -> destino no acervo
SUBPASTA_EIXO = {
    "realismo-frances": "frances",
    "romantismo-e-seguintes": "romantismo",
    "realismo-ingles": "anglo-saxoes",
    "modernismo-e-experimental": "modernismo",
    "antigos-e-classicos": "antigos",
    "nao-classificado": "outros",
}

# titulo em ingles p/ fallback de busca (obra nao esta na estante ou composta)
TITULO_EN = {
    1: "The Second Sex", 2: "Wind, Sand and Stars", 4: "Babbitt",
    5: "The Sun Also Rises", 6: "Ivanhoe", 8: "The Decameron",
    9: "Candide", 11: "Lost Illusions", 13: "Lord Jim",
    15: "The Consciousness of Zeno", 16: "Os Amores", 17: "The Pickwick Papers",
    18: "1919", 19: "Germinal", 21: "Cyrano de Bergerac", 22: "Nostradamus",
    23: "The Beautiful and Damned", 24: "The Grapes of Wrath",
    27: "Wuthering Heights", 28: "The Red and the Black", 29: "Les Fleurs du mal",
    31: "Reason and Passion", 32: "The Picture of Dorian Gray",
    34: "Women in Love", 35: "Tom Jones", 36: "Les Liaisons dangereuses",
    38: "The Trial", 39: "Long Day's Journey into Night",
    40: "Tales of Mystery and Imagination", 41: "Novelas Exemplares",
    42: "The House of the Seven Gables", 43: "Gulliver's Travels",
    44: "Sanctuary", 46: "Dead Souls", 47: "Moll Flanders",
    51: "A Doll's House", 53: "Maria Stuart", 54: "La Religieuse",
    55: "Les Travailleurs de la mer",
    # compostos
    "Lady Barberina": "The Way It Came",
    "A Outra Volta do Parafuso": "The Turn of the Screw",
    "Tônio Kroeger": "Tonio Kroeger", "A Morte em Veneza": "Death in Venice",
    "O Falecido Mattia Pascal": "Il Mattia Pascal",
    "Seis Personagens à Procura de um Autor": "Sei personaggi in cerca d'autore",
    "Tartufo": "Tartuffe", "A Escola de Mulheres": "L'École des femmes",
    "O Burguês Fidalgo": "Le Bourgeois gentilhomme",
    "Estado de Sítio": "L'État de siège", "O Estrangeiro": "L'Étranger",
    "Pequenos Burgueses": "Meščane", "Mãe": "Mat'",
    "As Três Irmãs": "Three Sisters", "Contos": "Short Stories",
    "Fausto": "Faust", "Werther": "Die Leiden des jungen Werthers",
}

# obras que no acervo estao em INGLES ou CORROMPIDAS -> prioridade alta (gap de idioma)
GAP_IDIOMA = {14, 20, 30, 37}

# ---------------------------------------------------------------------------
# 3. ALIASES de titulo — a mesma obra com OUTRO titulo em PT.
# ---------------------------------------------------------------------------
# BUG (2026-11-05): 4 obras do catalogo foram marcadas "sem candidato acima
# do limiar" porque o z-library publica a obra com um titulo PT DIFERENTE do
# catalogo:
#   - "A Wise Blood" (Flannery O'Connor) -> no z-library: "Sangue Sabio"
#   - "A Utopia" (Conrad)                  -> "sob o Olho do Ocidente"
#   - "Nostradamus: O Segredo das Centurias" -> "O Segredo das Centurias"
# A cobertura do titulo exigia PT **e** EN ao mesmo tempo, e nenhuma das
# formas casava. Agora o pipeline aceita ALIASES: a mesma obra procurada
# pelo nome que ela tem no acervo brasileiro.
# Chave: (titulo, autor) normalizados. Valor: lista de titulos alternativos.
#
# BUG (2026-11-08): "Retratos" (Joyce) tinha como alias "Retrato do Artista
# quando Jovem" — que e' UMA OUTRA OBRA (o romance). O alias foi herdado de
# uma suposicao errada e na rodada de 2026-11-08 fez o pipeline baixar o
# ROMANCE para a vaga que pedia DUBLINERS (contos). O acervo ficou com o
# livro errado, e o "Retratos" (Dubliners) continuou pendente.
# REGRA: um alias tem de ser o MESMO livro com outro titulo. "Retratos" (que
# no acervo brasileiro = Dublineses) nao pode apontar para "Retrato do
# Artista". Corrigido: o alias correto de Dublineses e' "Dublineses".
TITULOS_ALT = {
    ("a wise blood", "flannery o'connor"): ["Sangue Sábio"],
    ("retratos", "james joyce"): ["Dublineses"],
    # "Good Country People" (1955) e' um CONTO, que no PT-BR esta dentro
    # de "Contos completos" (Flannery O'Connor). Sem este alias, o pipeline
    # nao achava o titulo PT e baixava "Sangue Sabio" (= A Wise Blood).
    ("sangue bom", "flannery o'connor"): ["Contos completos",
                                          "Belas Personas"],
    ("a utopia", "joseph conrad"): ["Sob o Olho do Ocidente",
                                    "Under Western Eyes"],
    ("nostradamus: o segredo das centúrias", "pellos c. plavgo"):
        ["O Segredo das Centúrias", "Nostradamus"],
    ("o morro dos ventos uivantes", "emily brontë"):
        ["Wuthering Heights"],
    ("o pequeno príncipe", "antoine de saint-exupéry"):
        ["O Principezinho"],
    ("o poder e a glória", "graham greene"): ["A Potência e a Glória"],
    ("o problema da dor", "c. s. lewis"): ["O Problema do Sofrimento"],
    ("o sol também se levanta", "ernest hemingway"):
        ["The Sun Also Rises", "Também o Sol Se Levanta"],
    # Eça de Queiroz: o z-library publica com grafia variaca.
    ("a capital", "eça de queiroz"): ["A Capital", "A Capital (Eça de Queiroz)"],
    # BUG (2026-11-11): o z-library NAO tem "O Conde de Abranhos" isolado —
    # so tem ANTOLOGIAS de contos que o contem. Sem estes aliases, a obra
    # ficava "sem candidato" para sempre (o gate de titulo exige o nome
    # exato). Medido: "Contos" (id 4950065), "Coletânea de contos de Eça de
    # Queirós" (id 116638841), "7 melhores contos de Eça de Queirós".
    ("o conde de abranhos", "eça de queiroz"): ["O Conde de Abranhos",
                                                 "Conde de Abranhos",
                                                 "Coletânea de contos",
                                                 "7 melhores contos"],
    ("alves & c.ª", "eça de queiroz"): ["Alves & Cia", "Alves & C.ª", "Alves e Cia"],
    ("o mandarim", "eça de queiroz"): ["O Mandarim"],
    # BUG (2026-11-26): "Eugênio Oneguin" ficou "sem candidato" para sempre.
    # O catalogo so' buscava pelo titulo PT e pelo CIRILICO (Евгений Онегин),
    # e o z-library nao indexa o cirilico. A traducao PT-BR existe (Amora,
    # 2022) sob o titulo "Eugene Onegin" — grafia EN, edicao brasileira.
    # Medido: 50 resultados, 2 em Portuguese ("Eugene Onegin", ids 26591910
    # e 26769203).
    ("eugenio oneguin", "aleksandr puchkin"): ["Eugene Onegin", "Evgeny Onegin",
                                               "Eugenio Oneguin",
                                               # BUG (2026-11-26): a traducao
                                               # BRASILEIRA usa outra
                                               # transliteracao — "Evguiêni
                                               # Oniéguin". Medido: 3 edicoes
                                               # PT-BR (ids 119195136,
                                               # 24018157, 24308128). Sem este
                                               # alias o pipeline baixava a
                                               # edicao inglesa.
                                               "Evguiêni Oniéguin",
                                               "Evgueni Onieguin"],
    # BUG (2026-11-11): "A Perdição" (conto do Eça) nao existe ISOLADO no
    # z-library — so em antologias ("Contos", "Coletânea de contos",
    # "Obras Completas IV: Contos Completos"). Sem estes aliases, a busca
    # devolvia romances cujo titulo contem "perdição" ("Minha perdição",
    # "Aposta na perdição") e o gate de conteudo rejeitava todos.
    ("a perdição", "eça de queiroz"): ["A Perdição", "A Perdição",
                                      "Coletânea de contos",
                                      "7 melhores contos",
                                      "Obras Completas de Eça de Queirós IV"],
    # --- aliases medidos no z-library em 2026-11-11 (titulo REAL publicado) ---
    # Dickens: o PT-BR e' "Um Conto de Duas Cidades" (nao "Uma Historia de").
    ("uma história de duas cidades", "charles dickens"):
        ["Um Conto de Duas Cidades", "A História de Duas Cidades"],
    # Pirandello: o PT-BR e' "Seis personagens em busca de um autor".
    ("seis personagens à procura de um autor", "luigi pirandello"):
        ["Seis personagens em busca de um autor", "Sei personaggi in cerca d'autore"],
    # Goethe: o PT-BR e' "Os sofrimentos do jovem Werther".
    ("werther", "j. w. goethe"): ["Os Sofrimentos do Jovem Werther",
                                 "Sofrimentos do Jovem Werther"],
    ("tom jones", "henry fielding"): ["Tom Jones"],
    ("o peregrino", "john bunyan"): ["O Caminho do Peregrino",
                                     "O Peregrino (Clássicos MC)"],
    ("tônio kroeger", "thomas mann"): ["Tonio Kroeger", "Tonio Kröger"],
    # Flannery O'Connor: o PT-BR de "Good Country People" esta em
    # "Um homem bom e dificil de encontrar e outras historias".
    ("sangue bom", "flannery o'connor"): ["Um Homem Bom É Difícil de Encontrar "
                                          "e Outras Histórias"],
}


# ---------------------------------------------------------------------------
# 2. Complementares (rampa #140-#144 + trilha crista + degrau 5)
#    (titulo, autor, prioridade, subpasta, titulo_en, tags, ano)
# ---------------------------------------------------------------------------
COMPLEMENTARES = [
    # --- degrau 1: calibragem de gosto (nao estao na estante) ---
    ("O Pequeno Príncipe", "Antoine de Saint-Exupéry", "alta", "antigos",
     "Le Petit Prince", ["literatura", "conto", "canon-literario", "frances"], 1943),
    ("O Grande Gatsby", "F. Scott Fitzgerald", "alta", "anglo-saxoes",
     "The Great Gatsby", ["literatura", "romance", "canon-literario", "ingles"], 1925),
    ("Pedro Páramo", "Juan Rulfo", "alta", "mexicano",
     "Pedro Páramo", ["literatura", "romance", "mexicano"], 1955),
    ("Contos", "Edgar Allan Poe", "alta", "anglo-saxoes",
     "The Works of Edgar Allan Poe", ["literatura", "conto", "canon-literario", "ingles"], 1845),
    ("Contos", "Anton Tchekhov", "alta", "russo",
     "Stories", ["literatura", "conto", "canon-literario", "russo"], 1888),
    ("Contos", "Guy de Maupassant", "alta", "frances",
     "Contes", ["literatura", "conto", "canon-literario", "frances"], 1884),
    ("Contos", "Katherine Mansfield", "alta", "anglo-saxoes",
     "The Garden Party and Other Stories", ["literatura", "conto", "ingles"], 1922),
    ("Contos", "Nikolai Gógol", "alta", "russo",
     "Повести", ["literatura", "conto", "canon-literario", "russo"], 1835),
    ("Contos", "Ivan Turgenev", "alta", "russo",
     "Stories", ["literatura", "conto", "russo"], 1856),
    # --- degrau 5: romance experimental ---
    ("Cem Anos de Solidão", "Gabriel García Márquez", "alta", "mexicano",
     "Cien años de soledad", ["literatura", "romance", "mexicano", "canon-literario"], 1967),
    # BUG (2026-11-11): "Sob o Olho do Ocidente" (o PT-BR de "Under Western
    # Eyes") NAO existe no z-library (0 resultado medido). Sem a tag
    # "gap-idioma", o pipeline gastava cota com a edicao inglesa e depois
    # REJEITAVA o proprio download por "idioma-nao-pt" — a obra ficava
    # pendente e a cota evaporava.
    ("A Utopia", "Joseph Conrad", "media", "anglo-saxoes",
     "Under Western Eyes", ["literatura", "romance", "anglo-saxoes",
                            "gap-idioma"], 1911),
    ("O Coração das Trevas", "Joseph Conrad", "media", "anglo-saxoes",
     "Heart of Darkness", ["literatura", "romance", "canon-literario", "ingles"], 1899),
    # BUG (2026-11-11): o unico exemplar "portuguese" do z-library
    # ("Dublineses", id 23905843) e' uma traducao ESPANHOLA com metadados
    # em portugues — o gate de idioma pegou (es 41% vs pt 18%). Sem a tag
    # "gap-idioma", a obra ficava pendente; o exemplar EN existe e serve.
    ("Retratos", "James Joyce", "media", "anglo-saxoes",
     "Dubliners", ["literatura", "conto", "modernismo", "ingles",
                   "gap-idioma"], 1914),
    ("Mrs Dalloway", "Virginia Woolf", "media", "anglo-saxoes",
     "Mrs Dalloway", ["literatura", "romance", "modernismo", "ingles"], 1925),
    # --- trilha crista (#143): zero ficcao crista na estante ---
    ("Ortodoxia", "G. K. Chesterton", "alta", "ingles",
     "Orthodoxy", ["literatura", "ficcao-crista", "ingles", "apologetica"], 1908),
    ("O Homem que foi Quinta-feira", "G. K. Chesterton", "media", "ingles",
     "The Man Who Was Thursday", ["literatura", "ficcao-crista", "ingles"], 1908),
    ("O Problema da Dor", "C. S. Lewis", "alta", "ingles",
     "The Problem of Pain", ["literatura", "ficcao-crista", "ingles", "teologia"], 1940),
    ("O Peregrino", "John Bunyan", "alta", "ingles",
     "The Pilgrim's Progress", ["literatura", "ficcao-crista", "ingles", "teologia"], 1678),
    ("O Poder e a Glória", "Graham Greene", "alta", "ingles",
     "The Power and the Glory", ["literatura", "ficcao-crista", "ingles"], 1940),
    ("A Wise Blood", "Flannery O'Connor", "media", "ingles",
     "Wise Blood", ["literatura", "ficcao-crista", "ingles"], 1952),
    # BUG (2026-11-08): "Good Country People" (1955) e' um CONTO. O PT-BR
    # dele esta dentro de "Contos completos" (Flannery O'Connor) — nao como
    # um livro separado. O pipeline procurava o titulo PT e nao achava, e
    # acabava baixando "Sangue Sabio" (que e' A Wise Blood, outra obra).
    # Alias corrigido para o volume PT-BR onde o conto esta.
    ("Sangue Bom", "Flannery O'Connor", "media", "ingles",
     "Good Country People", ["literatura", "ficcao-crista", "ingles"], 1955),
    # --- rampa de leitura do William (ordem consolidada, nota 06) ---
    # "A Capital" e' o PRIMEIRO livro da rampa. O William tem o Volume III das
    # Obras de Eça de Queiroz em casa (E58), mas a edicao digital permite
    # leitura por tela (celular na rua) e citacao literal — o material de
    # prova da IPB precisa do texto, nao do Sumario do volume.
    ("A Capital", "Eça de Queiroz", "alta", "portugues",
     "A Capital", ["literatura", "romance", "canon-literario", "portugues",
                   "rampa-leitura", "primeiro-da-rampa"], 1893),
    # --- #184: PROVA DE LITERATURA IPB (prioridade MAXIMA) -----------------
    # O Manual do Aspirante nomeia as obras de leitura obrigatoria da prova de
    # Literatura Brasileira, e a LISTA MUDA A CADA ANO. Medido nos 4 Manuais
    # (2023 v1, 2024 v5, 2025 v3, 2026 v2). O Manual de 2027 ainda nao existe
    # -> a estrategia e ter TODOS os titulos ja usados.
    # Ja no acervo: A Hora da Estrela, Memorias Postumas, Policarpo Quaresma,
    # Santidade (Ryle). Faltam os 5 de baixo + O Pequeno Principe.
    ("A Moreninha", "Joaquim Manuel de Macedo", "maxima", "brasileira",
     "A Moreninha", ["literatura", "romance", "brasileira", "prova-ipb",
                     "leitura-obrigatoria"], 1844),
    ("Clarissa", "Érico Veríssimo", "maxima", "brasileira",
     "Clarissa", ["literatura", "romance", "brasileira", "prova-ipb",
                  "leitura-obrigatoria"], 1937),
    ("O Quinze", "Rachel de Queiroz", "maxima", "brasileira",
     "O Quinze", ["literatura", "romance", "brasileira", "prova-ipb",
                  "leitura-obrigatoria"], 1933),
    ("Com Vergonha do Evangelho", "John MacArthur", "alta", "teologia",
     "The Gospel According to Jesus", ["teologia", "apologetica", "prova-ipb",
                                       "leitura-obrigatoria"], 1988),
    ("Nossa Suficiência em Cristo", "John MacArthur", "alta", "teologia",
     "The Fulfillment of the Law", ["teologia", "apologetica", "prova-ipb",
                                    "leitura-obrigatoria"], 1991),
    # --- lacunas do Eca: as tres "Obras" da estante sao ANTOLOGIAS. As
    # obras unidades nao estao no acervo digital, entao entram no catalogo.
    ("O Conde de Abranhos", "Eça de Queiroz", "alta", "portugues",
     "O Conde de Abranhos", ["literatura", "conto", "canon-literario", "portugues"], 1893),
    ("Alves & C.ª", "Eça de Queiroz", "media", "portugues",
     "Alves & C.ª", ["literatura", "conto", "canon-literario", "portugues"], 1892),
    ("O Mandarim", "Eça de Queiroz", "alta", "portugues",
     "O Mandarim", ["literatura", "conto", "canon-literario", "portugues"], 1894),
    ("A Perdição", "Eça de Queiroz", "media", "portugues",
     "A Perdição", ["literatura", "conto", "canon-literario", "portugues"], 1894),
    # --- gap de idioma: classicos do acervo so em ingles ---
    ("Oliver Twist", "Charles Dickens", "alta", "anglo-saxoes",
     "Oliver Twist", ["literatura", "romance", "canon-literario", "ingles", "gap-idioma"], 1838),
    ("Uma História de Duas Cidades", "Charles Dickens", "media", "anglo-saxoes",
     "A Tale of Two Cities", ["literatura", "romance", "canon-literario", "ingles"], 1859),
    # --- autores com ZERO na estante: buracos de intencao ---
    # BUG (2026-11-11): o titulo PT estava ERRADO. "A Casa dos Espelhos" e'
    # "The Glass Bell" (1926) — um OUTRO livro de Woolf. A obra pedida aqui
    # (ano 1929) e' "A Room of One's Own", cujo titulo PT-BR e' "Um Teto Todo
    # Seu". Com o titulo errado, a busca nao achava nada e o acervo do
    # agente (que tem o "A Room of One's Own" com nome errado no _incoming)
    # ficava orfao.
    ("Um Teto Todo Seu", "Virginia Woolf", "media", "anglo-saxoes",
     "A Room of One's Own", ["literatura", "ensayo", "ingles", "feminismo"], 1929),
    ("Middlemarch", "George Eliot", "media", "anglo-saxoes",
     "Middlemarch", ["literatura", "romance", "canon-literario", "ingles"], 1871),
    ("Beloved", "Toni Morrison", "media", "anglo-saxoes",
     "Beloved", ["literatura", "romance", "ingles", "feminismo"], 1987),
    ("Se o Mundo Existisse", "Italo Calvino", "media", "italiano",
     "Se il mondo esistesse", ["literatura", "conto", "modernismo", "italiano"], 1983),
    # --- AMPLIACAO 2026-11-19 (rodada saturada: catalogo 94/94) --------------
    # Instrucao permanente do William (2026-11-18): "sempre amplie o catalogo".
    # Alvos MEDIDOS contra o acervo (nenhum existe hoje em data/biblioteca/).
    # Eixo 1: canon brasileiro (prova de Literatura IPB — a lista muda a cada
    # ano; o Manual 2027 ainda nao existe, entao entram os autores/titulos que
    # aparecem com mais frequencia nos Manuais 2023-2026).
    ("Quincas Borba", "Machado de Assis", "alta", "brasileira",
     "Quincas Borba", ["literatura", "romance", "brasileira", "prova-ipb"], 1891),
    ("Helena", "Machado de Assis", "alta", "brasileira",
     "Helena", ["literatura", "romance", "brasileira", "prova-ipb"], 1876),
    ("Esaú e Jacó", "Machado de Assis", "media", "brasileira",
     "Esau and Jacob", ["literatura", "romance", "brasileira", "prova-ipb"], 1904),
    ("O Alienista", "Machado de Assis", "alta", "brasileira",
     "O Alienista", ["literatura", "novela", "brasileira", "prova-ipb"], 1882),
    ("Senhora", "José de Alencar", "alta", "brasileira",
     "Senhora", ["literatura", "romance", "brasileira", "prova-ipb"], 1875),
    ("O Guarani", "José de Alencar", "media", "brasileira",
     "O Guarani", ["literatura", "romance", "brasileira", "prova-ipb"], 1857),
    ("O Cortiço", "Aluísio Azevedo", "alta", "brasileira",
     "O Cortico", ["literatura", "romance", "naturalismo", "brasileira", "prova-ipb"], 1890),
    ("O Ateneu", "Raul Pompeia", "media", "brasileira",
     "O Ateneu", ["literatura", "romance", "brasileira", "prova-ipb"], 1888),
    ("São Bernardo", "Graciliano Ramos", "alta", "brasileira",
     "Sao Bernardo", ["literatura", "romance", "brasileira", "prova-ipb"], 1934),
    ("Angústia", "Graciliano Ramos", "media", "brasileira",
     "Angustia", ["literatura", "romance", "brasileira"], 1936),
    ("A Paixão segundo G.H.", "Clarice Lispector", "alta", "brasileira",
     "A Paixao segundo G.H.", ["literatura", "romance", "brasileira", "prova-ipb"], 1964),
    ("Macunaíma", "Mário de Andrade", "alta", "brasileira",
     "Macunaima", ["literatura", "romance", "modernismo", "brasileira", "prova-ipb"], 1928),
    ("Sagarana", "João Guimarães Rosa", "media", "brasileira",
     "Sagarana", ["literatura", "conto", "brasileira", "prova-ipb"], 1946),
    ("Noite na Taverna", "Álvares de Azevedo", "media", "brasileira",
     "Noite na Taverna", ["literatura", "conto", "romantismo", "brasileira"], 1855),
    # Eixo 2: lacunas do Eca e do realismo portugues/frances
    ("O Primo Basílio", "Eça de Queiroz", "alta", "portugues",
     "O Primo Basilio", ["literatura", "romance", "canon-literario", "portugues"], 1878),
    ("Os Maias", "Eça de Queiroz", "alta", "portugues",
     "Os Maias", ["literatura", "romance", "canon-literario", "portugues"], 1888),
    # Eixo 3: classicos curtos que faltam (degraus baixos da rampa)
    ("O Velho e o Mar", "Ernest Hemingway", "alta", "anglo-saxoes",
     "The Old Man and the Sea", ["literatura", "novela", "canon-literario", "ingles"], 1952),
    ("A Metamorfose", "Franz Kafka", "alta", "alemão",
     "Die Verwandlung", ["literatura", "novela", "canon-literario", "alemao"], 1915),
    # Eixo 4: trilha de ficcao crista (a estante do William tem ZERO)
    ("O Grande Divórcio", "C. S. Lewis", "alta", "ingles",
     "The Great Divorce", ["literatura", "ficcao-crista", "ingles", "teologia"], 1945),
    ("Cartas de um Diabo a seu Aprendiz", "C. S. Lewis", "alta", "ingles",
     "The Screwtape Letters", ["literatura", "ficcao-crista", "ingles", "teologia"], 1942),

    # ===================================================================
    # AMPLIACAO 2026-11-20 — medido contra o acervo (1.335 .md + 2.279
    # titulos nas KBs): 130 obras de ficcao ausentes. Regra do William
    # (2026-11-18): rodada saturada NAO encerra o dia — amplia o catalogo.
    # ===================================================================
    # --- brasileira: prova de Literatura IPB + canone ---
    ("Memorial de Aires", "Machado de Assis", "maxima", "brasileira",
     "Memorial de Aires", ["literatura", "romance", "brasileira", "prova-ipb"], 1908),
    ("A Mão e a Luva", "Machado de Assis", "alta", "brasileira",
     "A Mão e a Luva", ["literatura", "romance", "brasileira"], 1874),
    ("Casa Velha", "Machado de Assis", "media", "brasileira",
     "Casa Velha", ["literatura", "romance", "brasileira"], 1885),
    ("Ressurreição", "Machado de Assis", "alta", "brasileira",
     "Ressurreição", ["literatura", "romance", "brasileira"], 1872),
    ("Lucíola", "José de Alencar", "alta", "brasileira",
     "Lucíola", ["literatura", "romance", "brasileira"], 1862),
    ("Ubirajara", "José de Alencar", "media", "brasileira",
     "Ubirajara", ["literatura", "romance", "brasileira"], 1874),
    ("Til", "José de Alencar", "media", "brasileira",
     "Til", ["literatura", "romance", "brasileira"], 1872),
    ("Casa de Pensão", "Aluísio Azevedo", "alta", "brasileira",
     "Casa de Pensão", ["literatura", "romance", "brasileira", "naturalismo"], 1884),
    ("O Mulato", "Aluísio Azevedo", "alta", "brasileira",
     "O Mulato", ["literatura", "romance", "brasileira", "naturalismo"], 1881),
    ("Bom Crioulo", "Adolfo Caminha", "media", "brasileira",
     "Bom Crioulo", ["literatura", "romance", "brasileira"], 1895),
    ("A Normalista", "Adolfo Caminha", "baixa", "brasileira",
     "A Normalista", ["literatura", "romance", "brasileira"], 1893),
    ("Inocência", "Visconde de Taunay", "media", "brasileira",
     "Inocência", ["literatura", "romance", "brasileira", "regionalismo"], 1872),
    ("Primeiras Estórias", "João Guimarães Rosa", "alta", "brasileira",
     "Primeiras Estórias", ["literatura", "conto", "brasileira"], 1962),
    ("Corpo de Baile", "João Guimarães Rosa", "alta", "brasileira",
     "Corpo de Baile", ["literatura", "romance", "brasileira"], 1956),
    ("No Urubuquaquá, no Pinhém", "João Guimarães Rosa", "media", "brasileira",
     "No Urubuquaquá, no Pinhém", ["literatura", "novela", "brasileira"], 1956),
    ("Memórias do Cárcere", "Graciliano Ramos", "alta", "brasileira",
     "Memórias do Cárcere", ["literatura", "memorias", "brasileira"], 1953),
    ("Fogo Morto", "José Lins do Rego", "alta", "brasileira",
     "Fogo Morto", ["literatura", "romance", "brasileira", "regionalismo"], 1943),
    ("Menino de Engenho", "José Lins do Rego", "media", "brasileira",
     "Menino de Engenho", ["literatura", "romance", "brasileira", "regionalismo"], 1932),
    ("Capitães da Areia", "Jorge Amado", "alta", "brasileira",
     "Capitães da Areia", ["literatura", "romance", "brasileira"], 1937),
    ("Dona Flor e Seus Dois Maridos", "Jorge Amado", "alta", "brasileira",
     "Dona Flor e Seus Dois Maridos", ["literatura", "romance", "brasileira"], 1966),
    ("Gabriela, Cravo e Canela", "Jorge Amado", "alta", "brasileira",
     "Gabriela, Cravo e Canela", ["literatura", "romance", "brasileira"], 1958),
    ("Tieta do Agreste", "Jorge Amado", "media", "brasileira",
     "Tieta do Agreste", ["literatura", "romance", "brasileira"], 1977),
    ("Jubiabá", "Jorge Amado", "media", "brasileira",
     "Jubiabá", ["literatura", "romance", "brasileira"], 1935),
    ("Mar Morto", "Jorge Amado", "media", "brasileira",
     "Mar Morto", ["literatura", "romance", "brasileira"], 1936),
    ("Lavoura Arcaica", "Raduan Nassar", "alta", "brasileira",
     "Lavoura Arcaica", ["literatura", "romance", "brasileira"], 1975),
    ("Um Copo de Cólera", "Raduan Nassar", "media", "brasileira",
     "Um Copo de Cólera", ["literatura", "novela", "brasileira"], 1978),
    ("Feliz Ano Novo", "Rubem Fonseca", "media", "brasileira",
     "Feliz Ano Novo", ["literatura", "conto", "brasileira"], 1975),
    ("A Grande Arte", "Rubem Fonseca", "media", "brasileira",
     "A Grande Arte", ["literatura", "romance", "brasileira"], 1983),
    ("O Filho Eterno", "Cristovão Tezza", "alta", "brasileira",
     "O Filho Eterno", ["literatura", "romance", "brasileira"], 2007),
    ("Leite Derramado", "Chico Buarque", "media", "brasileira",
     "Leite Derramado", ["literatura", "romance", "brasileira"], 2009),
    ("Budapeste", "Chico Buarque", "media", "brasileira",
     "Budapeste", ["literatura", "romance", "brasileira"], 2003),
    ("Terra Sonâmbula", "Mia Couto", "alta", "portugues",
     "Terra Sonâmbula", ["literatura", "romance", "portugues", "africano"], 1992),
    ("O Último Voo do Flamingo", "Mia Couto", "media", "portugues",
     "O Último Voo do Flamingo", ["literatura", "romance", "portugues", "africano"], 2000),
    ("A Hora dos Ruminantes", "José J. Veiga", "media", "brasileira",
     "A Hora dos Ruminantes", ["literatura", "romance", "brasileira"], 1966),
    ("Quarup", "Antônio Callado", "media", "brasileira",
     "Quarup", ["literatura", "romance", "brasileira"], 1967),
    ("Zero", "Ignácio de Loyola Brandão", "media", "brasileira",
     "Zero", ["literatura", "romance", "brasileira"], 1974),
    ("As Meninas", "Lygia Fagundes Telles", "alta", "brasileira",
     "As Meninas", ["literatura", "romance", "brasileira"], 1973),
    ("Ciranda de Pedra", "Lygia Fagundes Telles", "media", "brasileira",
     "Ciranda de Pedra", ["literatura", "romance", "brasileira"], 1954),
    ("Perto do Coração Selvagem", "Clarice Lispector", "alta", "brasileira",
     "Perto do Coração Selvagem", ["literatura", "romance", "brasileira"], 1943),
    ("A Paixão Segundo G.H.", "Clarice Lispector", "alta", "brasileira",
     "A Paixão Segundo G.H.", ["literatura", "romance", "brasileira"], 1964),
    # --- portuguesas ---
    ("Ensaio sobre a Cegueira", "José Saramago", "alta", "portugues",
     "Ensaio sobre a Cegueira", ["literatura", "romance", "portugues"], 1995),
    ("Memorial do Convento", "José Saramago", "alta", "portugues",
     "Memorial do Convento", ["literatura", "romance", "portugues"], 1982),
    ("O Evangelho segundo Jesus Cristo", "José Saramago", "media", "portugues",
     "O Evangelho segundo Jesus Cristo", ["literatura", "romance", "portugues"], 1991),
    ("A Jangada de Pedra", "José Saramago", "media", "portugues",
     "A Jangada de Pedra", ["literatura", "romance", "portugues"], 1986),
    ("O Ano da Morte de Ricardo Reis", "José Saramago", "media", "portugues",
     "O Ano da Morte de Ricardo Reis", ["literatura", "romance", "portugues"], 1984),
    ("Mensagem", "Fernando Pessoa", "alta", "portugues",
     "Mensagem", ["literatura", "poesia", "portugues"], 1934),
    ("Livro do Desassossego", "Fernando Pessoa", "alta", "portugues",
     "Livro do Desassossego", ["literatura", "prosa", "portugues"], 1982),
    ("Os Lusíadas", "Luís de Camões", "alta", "portugues",
     "Os Lusíadas", ["literatura", "epopeia", "portugues", "prova-ipb"], 1572),
    ("Amor de Perdição", "Camilo Castelo Branco", "alta", "portugues",
     "Amor de Perdição", ["literatura", "romance", "portugues"], 1862),
    ("Viagens na Minha Terra", "Almeida Garrett", "media", "portugues",
     "Viagens na Minha Terra", ["literatura", "prosa", "portugues"], 1846),
    ("A Sibila", "Agustina Bessa-Luís", "media", "portugues",
     "A Sibila", ["literatura", "romance", "portugues"], 1954),
    ("As Naus", "António Lobo Antunes", "baixa", "portugues",
     "As Naus", ["literatura", "romance", "portugues"], 1988),
    ("O Delfim", "José Cardoso Pires", "media", "portugues",
     "O Delfim", ["literatura", "romance", "portugues"], 1968),
    # --- italiano ---
    ("O Nome da Rosa", "Umberto Eco", "alta", "italiano",
     "Il nome della rosa", ["literatura", "romance", "italiano"], 1980),
    ("O Pêndulo de Foucault", "Umberto Eco", "media", "italiano",
     "Il pendolo di Foucault", ["literatura", "romance", "italiano"], 1988),
    ("As Cidades Invisíveis", "Italo Calvino", "alta", "italiano",
     "Le città invisibili", ["literatura", "romance", "italiano"], 1972),
    ("Se um Viajante numa Noite de Inverno", "Italo Calvino", "media", "italiano",
     "Se una notte d'inverno un viaggiatore", ["literatura", "romance", "italiano"], 1979),
    ("O Barão nas Árvores", "Italo Calvino", "alta", "italiano",
     "Il barone rampante", ["literatura", "romance", "italiano"], 1957),
    ("O Deserto dos Tártaros", "Dino Buzzati", "alta", "italiano",
     "Il deserto dei Tartari", ["literatura", "romance", "italiano"], 1940),
    ("É Isto um Homem?", "Primo Levi", "alta", "italiano",
     "Se questo è un uomo", ["literatura", "memorias", "italiano"], 1947),
    ("A Trégua", "Primo Levi", "media", "italiano",
     "La tregua", ["literatura", "memorias", "italiano"], 1963),
    ("Léxico Familiar", "Natalia Ginzburg", "alta", "italiano",
     "Lessico famigliare", ["literatura", "memorias", "italiano"], 1963),
    ("A Pele", "Curzio Malaparte", "media", "italiano",
     "La pelle", ["literatura", "romance", "italiano"], 1949),
    ("Os Noivos", "Alessandro Manzoni", "media", "italiano",
     "I promessi sposi", ["literatura", "romance", "italiano"], 1827),
    # --- russo ---
    ("Pais e Filhos", "Ivan Turguêniev", "alta", "russo",
     "Отцы и дети", ["literatura", "romance", "russo"], 1862),
    ("Oblomov", "Ivan Gontcharov", "alta", "russo",
     "Обломов", ["literatura", "romance", "russo"], 1859),
    ("Eugênio Oneguin", "Aleksandr Púchkin", "media", "russo",
     "Евгений Онегин", ["literatura", "poesia", "russo"], 1833),
    ("Um Herói do Nosso Tempo", "Mikhail Lermontov", "media", "russo",
     "Герой нашего времени", ["literatura", "romance", "russo"], 1840),
    ("O Mestre e Margarida", "Mikhail Bulgákov", "alta", "russo",
     "Мастер и Маргарита", ["literatura", "romance", "russo"], 1967),
    ("A Sonata a Kreutzer", "Liev Tolstói", "media", "russo",
     "Крейцерова соната", ["literatura", "novela", "russo"], 1889),
    ("Noites Brancas", "Fiódor Dostoiévski", "alta", "russo",
     "Белые ночи", ["literatura", "novela", "russo"], 1848),
    ("Recordações da Casa dos Mortos", "Fiódor Dostoiévski", "media", "russo",
     "Записки из Мёртвого дома", ["literatura", "romance", "russo"], 1862),
    # --- alemao ---
    ("Sidarta", "Hermann Hesse", "alta", "alemão",
     "Siddhartha", ["literatura", "romance", "alemao"], 1922),
    ("O Lobo da Estepe", "Hermann Hesse", "alta", "alemão",
     "Der Steppenwolf", ["literatura", "romance", "alemao"], 1927),
    ("O Tambor", "Günter Grass", "media", "alemão",
     "Die Blechtrommel", ["literatura", "romance", "alemao"], 1959),
    ("A Morte de Virgílio", "Hermann Broch", "baixa", "alemão",
     "Der Tod des Vergil", ["literatura", "romance", "alemao"], 1945),
    ("O Homem sem Qualidades", "Robert Musil", "baixa", "alemão",
     "Der Mann ohne Eigenschaften", ["literatura", "romance", "alemao"], 1930),
    ("Carta ao Pai", "Franz Kafka", "alta", "alemão",
     "Brief an den Vater", ["literatura", "cartas", "alemao"], 1919),
    ("América", "Franz Kafka", "media", "alemão",
     "Der Verschollene", ["literatura", "romance", "alemao"], 1927),
    # --- ingles ---
    ("Hamlet", "William Shakespeare", "alta", "ingles",
     "Hamlet", ["literatura", "teatro", "ingles"], 1603),
    ("Macbeth", "William Shakespeare", "alta", "ingles",
     "Macbeth", ["literatura", "teatro", "ingles"], 1623),
    ("Rei Lear", "William Shakespeare", "alta", "ingles",
     "King Lear", ["literatura", "teatro", "ingles"], 1608),
    ("Otelo", "William Shakespeare", "alta", "ingles",
     "Othello", ["literatura", "teatro", "ingles"], 1604),
    ("A Tempestade", "William Shakespeare", "media", "ingles",
     "The Tempest", ["literatura", "teatro", "ingles"], 1611),
    ("Sonhos de uma Noite de Verão", "William Shakespeare", "media", "ingles",
     "A Midsummer Night's Dream", ["literatura", "teatro", "ingles"], 1600),
    ("Feira das Vaidades", "William Makepeace Thackeray", "media", "anglo-saxoes",
     "Vanity Fair", ["literatura", "romance", "ingles"], 1848),
    ("Tess dos d'Urbervilles", "Thomas Hardy", "alta", "anglo-saxoes",
     "Tess of the d'Urbervilles", ["literatura", "romance", "ingles"], 1891),
    ("Judas, o Obscuro", "Thomas Hardy", "media", "anglo-saxoes",
     "Jude the Obscure", ["literatura", "romance", "ingles"], 1895),
    ("Admirável Mundo Novo", "Aldous Huxley", "alta", "anglo-saxoes",
     "Brave New World", ["literatura", "romance", "ingles", "distopia"], 1932),
    ("O Senhor das Moscas", "William Golding", "alta", "anglo-saxoes",
     "Lord of the Flies", ["literatura", "romance", "ingles"], 1954),
    ("Tristram Shandy", "Laurence Sterne", "baixa", "anglo-saxoes",
     "The Life and Opinions of Tristram Shandy", ["literatura", "romance", "ingles"], 1759),
    ("A Marcha de Radetzky", "Joseph Roth", "media", "alemão",
     "Radetzkymarsch", ["literatura", "romance", "alemao"], 1932),
    # --- frances ---
    ("Os Três Mosqueteiros", "Alexandre Dumas", "alta", "frances",
     "Les Trois Mousquetaires", ["literatura", "romance", "frances"], 1844),
    ("O Conde de Monte Cristo", "Alexandre Dumas", "alta", "frances",
     "Le Comte de Monte-Cristo", ["literatura", "romance", "frances"], 1844),
    ("A Dama das Camélias", "Alexandre Dumas Filho", "media", "frances",
     "La Dame aux camélias", ["literatura", "romance", "frances"], 1848),
    ("A Cartuxa de Parma", "Stendhal", "alta", "frances",
     "La Chartreuse de Parme", ["literatura", "romance", "frances"], 1839),
    ("A Educação Sentimental", "Gustave Flaubert", "media", "frances",
     "L'Éducation sentimentale", ["literatura", "romance", "frances"], 1869),
    ("Nana", "Émile Zola", "media", "frances",
     "Nana", ["literatura", "romance", "frances", "naturalismo"], 1880),
    ("Os Miseráveis", "Victor Hugo", "alta", "frances",
     "Les Misérables", ["literatura", "romance", "frances"], 1862),
    ("O Corcunda de Notre-Dame", "Victor Hugo", "alta", "frances",
     "Notre-Dame de Paris", ["literatura", "romance", "frances"], 1831),
    ("Cândido", "Voltaire", "alta", "frances",
     "Candide", ["literatura", "conto", "frances"], 1759),
    ("Cartas Persas", "Montesquieu", "baixa", "frances",
     "Lettres persanes", ["literatura", "romance", "frances"], 1721),
    ("A Princesa de Clèves", "Madame de La Fayette", "media", "frances",
     "La Princesse de Clèves", ["literatura", "romance", "frances"], 1678),
    # --- espanhol / latino-americano ---
    ("Ficções", "Jorge Luis Borges", "alta", "mexicano",
     "Ficciones", ["literatura", "conto", "argentino"], 1944),
    ("O Aleph", "Jorge Luis Borges", "alta", "mexicano",
     "El Aleph", ["literatura", "conto", "argentino"], 1949),
    ("O Jogo da Amarelinha", "Julio Cortázar", "alta", "mexicano",
     "Rayuela", ["literatura", "romance", "argentino"], 1963),
    ("A Cidade e os Cachorros", "Mario Vargas Llosa", "media", "mexicano",
     "La ciudad y los perros", ["literatura", "romance", "peruano"], 1963),
    ("Conversa na Catedral", "Mario Vargas Llosa", "media", "mexicano",
     "Conversación en La Catedral", ["literatura", "romance", "peruano"], 1969),
    ("A Morte de Artemio Cruz", "Carlos Fuentes", "media", "mexicano",
     "La muerte de Artemio Cruz", ["literatura", "romance", "mexicano"], 1962),
    ("A Colmeia", "Camilo José Cela", "media", "mexicano",
     "La colmena", ["literatura", "romance", "espanhol"], 1951),
    ("A Regenta", "Leopoldo Alas Clarín", "baixa", "mexicano",
     "La Regenta", ["literatura", "romance", "espanhol"], 1884),
    ("Fortunata e Jacinta", "Benito Pérez Galdós", "baixa", "mexicano",
     "Fortunata y Jacinta", ["literatura", "romance", "espanhol"], 1887),
    # --- greco-latino (fonte da tradicao literaria ocidental) ---
    ("Ilíada", "Homero", "alta", "antigos",
     "Ἰλιάς", ["literatura", "epopeia", "grego", "canon-literario"], -750),
    ("Édipo Rei", "Sófocles", "alta", "antigos",
     "Οἰδίπους Τύραννος", ["literatura", "teatro", "grego", "canon-literario"], -429),
    ("Antígona", "Sófocles", "alta", "antigos",
     "Ἀντιγόνη", ["literatura", "teatro", "grego", "canon-literario"], -441),
    ("Medeia", "Eurípides", "media", "antigos",
     "Μήδεια", ["literatura", "teatro", "grego"], -431),
    ("Metamorfoses", "Ovídio", "media", "antigos",
     "Metamorphoses", ["literatura", "poesia", "latim", "canon-literario"], 8),
    ("O Asno de Ouro", "Apuleio", "media", "antigos",
     "Metamorphoseon", ["literatura", "romance", "latim"], 160),
    ("Satiricon", "Petrônio", "baixa", "antigos",
     "Satyricon", ["literatura", "romance", "latim"], 60),
    ("História da Guerra do Peloponeso", "Tucídides", "media", "antigos",
     "Ἱστορίαι", ["literatura", "historia", "grego"], -400),
    # --- seculo XX nao anglo/franco ---
    ("O Amante de Lady Chatterley", "D. H. Lawrence", "media", "anglo-saxoes",
     "Lady Chatterley's Lover", ["literatura", "romance", "ingles"], 1928),
    ("A Insustentável Leveza do Ser", "Milan Kundera", "alta", "modernismo",
     "Nesnesitelná lehkost bytí", ["literatura", "romance", "tcheco"], 1984),
    ("A Vida é Sonho", "Calderón de la Barca", "media", "mexicano",
     "La vida es sueño", ["literatura", "teatro", "espanhol"], 1635),

    # ===================================================================
    # AMPLIACAO 2026-11-27 — catalogo estava 236/236 adquirido (saturado),
    # o que travava a rodada em "0 baixados". Instrucao permanente do
    # William (2026-11-18): rodada saturada NAO encerra o dia — amplia.
    #
    # Cada alvo abaixo foi MEDIDO em 2026-11-27 de DUAS formas:
    #   (1) ausente do acervo: nenhum .md em data/biblioteca/ e nenhum
    #       `titulo` nas 1.742 entradas das KBs;
    #   (2) EXISTE em PT-BR: busca real no libgen (json.php) devolveu
    #       edicao "Portuguese" com EPUB/MOBI — nao e' alvo fantasma.
    # O z-library estava negando acesso ("Access denied") hoje; a 2a via
    # (libgen, sem cota) e' o caminho que funciona.
    # ===================================================================
    # --- eixo brasileira (canone + prova de Literatura IPB) ---
    ("Memorial de Maria Moura", "Rachel de Queiroz", "alta", "brasileira",
     "Memorial de Maria Moura", ["literatura", "romance", "brasileira"], 1992),
    ("A Escrava Isaura", "Bernardo Guimarães", "alta", "brasileira",
     "A Escrava Isaura", ["literatura", "romance", "brasileira", "prova-ipb"], 1875),
    ("Memórias de um Sargento de Milícias", "Manuel Antônio de Almeida", "alta",
     "brasileira", "Memórias de um Sargento de Milícias",
     ["literatura", "romance", "brasileira", "prova-ipb"], 1854),
    ("Recordações do Escrivão Isaías Caminha", "Lima Barreto", "alta", "brasileira",
     "Recordações do Escrivão Isaías Caminha",
     ["literatura", "romance", "brasileira", "prova-ipb"], 1909),
    ("Clara dos Anjos", "Lima Barreto", "media", "brasileira",
     "Clara dos Anjos", ["literatura", "romance", "brasileira"], 1948),
    ("O Tronco", "Bernardo Élis", "media", "brasileira",
     "O Tronco", ["literatura", "romance", "brasileira", "regionalismo"], 1956),
    # --- eixo seculo XX (narrativa moderna, alta rotacao na rampa) ---
    ("Enquanto Agonizo", "William Faulkner", "alta", "anglo-saxoes",
     "As I Lay Dying", ["literatura", "romance", "modernismo", "ingles"], 1930),
    ("O Som e a Fúria", "William Faulkner", "alta", "anglo-saxoes",
     "The Sound and the Fury", ["literatura", "romance", "modernismo", "ingles"], 1929),
    ("A Montanha Mágica", "Thomas Mann", "alta", "alemão",
     "Der Zauberberg", ["literatura", "romance", "canon-literario", "alemao"], 1924),
    ("Esperando Godot", "Samuel Beckett", "alta", "ingles",
     "En attendant Godot", ["literatura", "teatro", "modernismo"], 1953),
    ("Laranja Mecânica", "Anthony Burgess", "alta", "anglo-saxoes",
     "A Clockwork Orange", ["literatura", "romance", "distopia", "ingles"], 1962),
    ("O Conto da Aia", "Margaret Atwood", "alta", "anglo-saxoes",
     "The Handmaid's Tale", ["literatura", "romance", "distopia", "ingles"], 1985),
    ("Matadouro Cinco", "Kurt Vonnegut", "alta", "anglo-saxoes",
     "Slaughterhouse-Five", ["literatura", "romance", "ingles"], 1969),
    ("Fahrenheit 451", "Ray Bradbury", "alta", "anglo-saxoes",
     "Fahrenheit 451", ["literatura", "romance", "distopia", "ingles"], 1953),
    # --- eixo latino-americano (realismo magico) ---
    ("O Amor nos Tempos do Cólera", "Gabriel García Márquez", "alta", "mexicano",
     "El amor en los tiempos del cólera",
     ["literatura", "romance", "mexicano", "canon-literario"], 1985),
    ("Crônica de uma Morte Anunciada", "Gabriel García Márquez", "alta", "mexicano",
     "Crónica de una muerte anunciada",
     ["literatura", "romance", "mexicano"], 1981),
    ("A Casa dos Espíritos", "Isabel Allende", "media", "mexicano",
     "La casa de los espíritus", ["literatura", "romance", "chileno"], 1982),
]

# ---------------------------------------------------------------------------
def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


# indice normalizado (sem acento, minusculo) dos aliases. As chaves de
# TITULOS_ALT sao escritas como aparecem no YAML, mas a busca usa a forma
# normalizada — assim nao depende da grafia ("Emily Brontë" vs "Bronte").
ALIASES_NORM = {
    (sem_acento(t).lower().strip(), sem_acento(a).lower().strip()): v
    for (t, a), v in TITULOS_ALT.items()
}


def esc(s):
    """Escapa para YAML de forma segura (aspas simples, como o resto do repo)."""
    return "'" + str(s).replace("'", "''") + "'"


def main():
    import yaml
    est = yaml.safe_load(ESTANTE.read_text(encoding="utf-8"))
    itens = []
    vistos = set()

    def add(tit, aut, prio, sub, ten, tags, ano, origem, nota="", alt=None):
        chave = (sem_acento(tit).lower().strip(), sem_acento(aut).lower().strip())
        if chave in vistos:
            return
        vistos.add(chave)
        tags = list(tags) or ["literatura", "canon-literario"]
        bloco = {
            "titulo": tit, "autor": aut, "prioridade": prio, "tags": tags,
            "ano": ano, "subpasta": sub,
        }
        if ten:
            bloco["titulo_en"] = ten
        # alias: a mesma obra pode ter outro titulo no acervo PT.
        # A chave e' normalizada (sem acento, minuscula) no momento do uso, para
        # nao depender da grafia exata ("Emily Brontë" vs "Emily Bronte").
        alt_final = list(alt or []) + list(
            ALIASES_NORM.get((sem_acento(tit).lower().strip(),
                              sem_acento(aut).lower().strip()), []))
        if alt_final:
            bloco["titulos_alt"] = alt_final
        if origem:
            bloco["origem"] = origem
        if nota:
            bloco["nota"] = nota
        itens.append(bloco)

    # ---- 1. estante ----
    for lv in est["livros"]:
        i = lv["id"]
        if i in EXCLUIR:
            continue
        if lv.get("no_acervo_study_agent") in ("sim", "parcial"):
            # ja esta no acervo (legivel ou parcial): nao e' lacuna
            if i not in GAP_IDIOMA:
                continue
        aut = lv["autor"]
        eixo = lv.get("eixo") or "nao-classificado"
        sub = SUBPASTA_EIXO.get(eixo, "outros")
        base_tags = ["literatura", "canon-literario", "estante-william"]
        if i in GAP_IDIOMA:
            base_tags.append("gap-idioma")
            prio = "alta"
        elif lv.get("no_acervo_study_agent") == "parcial":
            prio = "media"
        else:
            prio = "alta"
        if i in COMPOSTOS:
            for tit, ten, subc in COMPOSTOS[i]:
                add(tit, aut, prio, subc, ten, base_tags + ["obra-unica"],
                    "", "estante-william",
                    "faz parte de um volume composto da estante — comprar SEPARADO")
        else:
            add(lv["titulo"], aut, prio, sub, TITULO_EN.get(i, ""),
                base_tags, "", "estante-william",
                "voce tem em casa; o acervo nao tem")

    # ---- 2. complementares ----
    for tit, aut, prio, sub, ten, tags, ano in COMPLEMENTARES:
        add(tit, aut, prio, sub, ten, tags, ano, "rampa-ficcao",
            "nao esta na sua estante — e' da rampa de leitura")

    # ---- saida ----
    ordem = {"alta": 0, "media": 1, "baixa": 2}
    itens.sort(key=lambda x: (ordem.get(x["prioridade"], 1), x["titulo"]))

    linhas = ["# Catalogo de aquisicao de ficcao — gerado por scripts/gerar-catalogo-ficcao.py",
              "# NAO EDITAR A MAO: edite a fonte (estante-william.yaml / lista-aquisicao.md)",
              "# e regerere. Consumido por scripts/pipeline-aquisicao.py",
              "catalogo:"]
    for it in itens:
        linhas.append(f"  - titulo: {esc(it['titulo'])}")
        linhas.append(f"    autor: {esc(it['autor'])}")
        linhas.append(f"    prioridade: {esc(it['prioridade'])}")
        linhas.append(f"    subpasta: {esc(it['subpasta'])}")
        linhas.append(f"    tags: [{', '.join(esc(t) for t in it['tags'])}]")
        if it.get("ano"):
            linhas.append(f"    ano: {it['ano']}")
        if it.get("titulo_en"):
            linhas.append(f"    titulo_en: {esc(it['titulo_en'])}")
        if it.get("titulos_alt"):
            linhas.append(f"    titulos_alt: [{', '.join(esc(t) for t in it['titulos_alt'])}]")
        if it.get("origem"):
            linhas.append(f"    origem: {esc(it['origem'])}")
        if it.get("nota"):
            linhas.append(f"    nota: {esc(it['nota'])}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(linhas) + "\n", encoding="utf-8")

    altas = sum(1 for i in itens if i["prioridade"] == "alta")
    print(f"OK {OUT.relative_to(ROOT)}: {len(itens)} obras "
          f"({altas} alta, {len(itens)-altas} media/baixa)")


if __name__ == "__main__":
    main()
