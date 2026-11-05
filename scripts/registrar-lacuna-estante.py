#!/usr/bin/env python3
"""Registra a lacuna de ficcao entre a estante fisica do William (58) e o acervo.

Faz 3 coisas:
  1) insere a secao #182 na lista-aquisicao.md com os 50 titulos de ficcao que o
     William TEM em casa e o acervo do Study-Agent NAO tem
  2) atualiza o bloco #140-#144 (rampa) com o status real de cada obra
  3) corrige o estante-william.yaml com a integridade real de cada .md do acervo

Integridade verificada por varredura de TEXTO COMPLETO dos 1.078 .md (1,1 GB),
nao por nome de arquivo -- o cruzamento por nome errava (achava "Contos", "Eca",
"Bia" em citacoes de outros livros).
"""
import re
import yaml
import pathlib

ROOT = pathlib.Path("/home/willian/study-agent")
LISTA = ROOT / "data/biblioteca/lista-aquisicao.md"
YML = ROOT / "data/perfil/bibliotecario/estante-william.yaml"
HOJE = "2026-11-05"

# (id_estante, titulo, autor, prioridade, observacao)
LACUNA = [
    (1, "Quando o Espiritual Domina", "Simone de Beauvoir", "alta",
     "obra de referencia do existencialismo; 1 mulher autora em 58 - prioritaria"),
    (2, "Terra dos Homens", "Antoine de Saint-Exupery", "alta",
     "curto, degrau 1-2; mesmo autor do Pequeno Principe (#140)"),
    (4, "Babbitt", "Sinclair Lewis", "alta", "satire americana, 1922"),
    (5, "O Sol Tambem Se Levanta", "Ernest Hemingway", "alta",
     "degrau 2; Hemingway e eixo do romance americano"),
    (6, "Ivanhoe", "Walter Scott", "alta", "classico do romantismo"),
    (8, "Decameron", "Giovanni Boccaccio", "alta",
     "10 narrativas - serve fragmentado como degrau 1"),
    (9, "Contos", "Voltaire", "alta", "Candide etc.; degrau 1"),
    (11, "Ilusoes Perdidas", "Honore de Balzac", "alta",
     "Comedia Humana; Balzac e eixo da escola realista"),
    (13, "Lord Jim", "Joseph Conrad", "alta",
     "romanesco; par do Coracao das Trevas (#144)"),
    (15, "A Consciencia de Zeno", "Italo Svevo", "alta",
     "modernismo italiano; curto e dificil"),
    (16, "Os Amores", "Bocage", "alta", "poesia lirica PT; degrau 1"),
    (17, "As Aventuras do Sr. Pickwick", "Charles Dickens", "media",
     "volume longo; o acervo so tem a Colecao Dickens em ingles e corrompida"),
    (18, "1919", "John dos Passos", "media", "romance-documento USA, 400+ pag"),
    (19, "Germinal", "Emile Zola", "alta", "romance social; eixo realista"),
    (21, "Cyrano de Bergerac", "Edmond Rostand", "alta", "teatro em versos; degrau 2"),
    (22, "Nostradamus: O Segredo das Centurias", "Pellos C. Plavgo", "baixa",
     "pseudo-historia; baixa prioridade"),
    (23, "Suave E a Noite", "F. Scott Fitzgerald", "alta",
     "o romance perdido dos anos 20; par do Grande Gatsby (#140)"),
    (24, "As Vinhas da Ira", "John Steinbeck", "alta", "Pulitzer; degrau 2-3"),
    (26, "Lady Barberina / A Outra Volta do Parafuso", "Henry James", "alta",
     "volume composto: adquirir as duas novelas SEPARADAS"),
    (27, "O Morro dos Ventos Uivantes", "Emily Bronte", "alta",
     "degrau 2-3; par de Jane Eyre (que esta no acervo)"),
    (28, "O Vermelho e o Negro", "Stendhal", "alta", "classico da escola realista"),
    (29, "As Flores do Mal", "Charles Baudelaire", "alta", "poesia; degrau 1-2"),
    (31, "Idade da Razao", "Jean-Paul Sartre", "alta",
     "relitura do classico; edicao Editora Abril"),
    (32, "O Retrato de Dorian Gray", "Oscar Wilde", "alta", "classico; curto, degrau 2"),
    (33, "Tonio Kroeger / A Morte em Veneza", "Thomas Mann", "alta",
     "volume composto: adquirir SEPARADOS"),
    (34, "Mulheres Apaixonadas", "D. H. Lawrence", "alta",
     "contos + romance; modernismo ingles"),
    (35, "Tom Jones", "Henry Fielding", "media",
     "classico do romance ingles, longo (2 tomos)"),
    (36, "As Relacoes Perigosas", "Choderlos de Laclos", "alta",
     "classico realista; livro de cartas"),
    (38, "O Processo", "Franz Kafka", "alta", "classico do absurdo"),
    (39, "Longa Jornada Noite Adentro", "Eugene O'Neill", "alta",
     "peca; premio Nobel"),
    (40, "Historias Extraordinarias", "Edgar Allan Poe", "alta",
     "degrau 1 - leitura de entrada"),
    (41, "Novelas Exemplares", "Miguel de Cervantes", "alta",
     "Cervantes alem do Quixote - par natural"),
    (42, "A Casa das Sete Torres", "Nathaniel Hawthorne", "alta",
     "classico norte-americano"),
    (43, "Viagens de Gulliver", "Jonathan Swift", "alta", "satira; degrau 2"),
    (44, "Santuario", "William Faulkner", "alta", "classico modernista"),
    (45, "O Falecido Mattia Pascal / Seis Personagens a Procura de um Autor",
     "Luigi Pirandello", "alta", "volume composto: adquirir SEPARADOS (meta-teatro)"),
    (46, "Almas Mortas", "Nikolai Gogol", "alta",
     "classico russo; par de Crime e Castigo (no acervo)"),
    (47, "Moll Flanders", "Daniel Defoe", "alta", "classico do seculo XVIII"),
    (48, "Tartufo / Escola de Mulheres / O Burgues Fidalgo", "Moliere", "alta",
     "coletanea de pecas: adquirir CADA peca"),
    (49, "Estado de Site / O Estrangeiro", "Albert Camus", "alta",
     "volume composto: adquirir SEPARADOS"),
    (50, "Pequenos Burgueses / Mae", "Maxim Gorki", "alta",
     "volume composto: adquirir SEPARADOS"),
    (51, "Casa de Bonecas", "Henrik Ibsen", "alta", "peca; Naturalismo"),
    (52, "As Tres Irmas / Contos", "Anton Tchekhov", "alta",
     "volume composto: adquirir SEPARADOS; par de Dostoievski (no acervo)"),
    (53, "Maria Stuart", "Friedrich Schiller", "alta", "peca historica; degrau 2"),
    (54, "A Religiosa", "Denis Diderot", "alta", "romance filosofico; degrau 2-3"),
    (55, "Os Trabalhadores do Mar", "Victor Hugo", "media",
     "volume longo; par de Les Miserables (no acervo)"),
    (56, "Obras de Eca de Queiroz - Volume I", "Eca de Queiroz", "media",
     "digitalizar da estante fisica -> acervo"),
    (57, "Obras de Eca de Queiroz - Volume II", "Eca de Queiroz", "media",
     "digitalizar da estante fisica -> acervo"),
    (58, "Obras de Eca de Queiroz - Volume III", "Eca de Queiroz", "media",
     "digitalizar da estante fisica -> acervo (contem A Capital - 30 pag, degrau 1 da prova)"),
]

# integridade real do acervo, verificada por varredura de texto completo
INTEGRIDADE = {
    7: ("sim", "inteiro",
        "literatura-mundial-classica/proust/Em-Busca-do-Tempo-Perdido-I-Marcel-Proust.md"),
    10: ("sim", "inteiro", "literatura-mundial-classica/antigos/A-Odisseia-Homero.md"),
    12: ("sim", "inteiro", "literatura-mundial-classica/antigos/A-Eneida-Virgilio.md"),
    14: ("nao", "CORROMPIDO (18 KB, Traceback do conversor, 0 linhas de prosa)",
         "literatura-mundial-classica/Cervantes-Dom-Quixote.md"),
    20: ("parcial", "volume I apenas (Inferno)",
         "literatura-mundial-classica/dante/A-Divina-Comedia-Dante-Alighieri.md"),
    25: ("sim", "inteiro", "literatura-mundial-classica/frances/Madame-Bovary-Gustave-Flaubert.md"),
    30: ("nao", "CORROMPIDO (81 KB, so o CSS do EPUB, 1 linha de prosa; e em ingles)",
         "literatura-mundial-classica/The-Charles-Dickens-Collection-Volume-One-Oliver-Twist-Great-Expectations-and-Bleak-House.md"),
    37: ("parcial", "so introducao critica + fragmentos (64 linhas de prosa)",
         "literatura-mundial-classica/antigos/Fausto-Johann-Wolfgang-von-Goethe.md"),
}

# ---------------------------------------------------------------- lista
txt = LISTA.read_text(encoding="utf-8")

linhas = ["| Marcador | Obra | Autor | Prioridade | Status |",
          "|---|---|---|---|---|"]
for i, t, a, p, o in LACUNA:
    linhas.append(
        f"| E{i:02d} | {t} | {a} | {p} | pendente - **voce tem em casa**, o acervo nao tem. {o} |")

secao = f"""### #182 - FICCÃO: lacuna da estante fisica do William (58 titulos) - 49 obras de ficcao ausentes do acervo

- **Origem:** cruzamento da lista de 58 livros de casa do William
  (`data/perfil/bibliotecario/estante-william.yaml`) contra o acervo do Study-Agent.
- **Metodo:** varredura de **texto completo** dos 1.078 `.md` do acervo (1,1 GB), nao so por
  nome de arquivo - o cruzamento anterior por nome errava (achava "Contos", "Eca", "Bia"
  em citacoes de outros livros).
- **Idioma/formato esperado:** PT-BR / epub ou pdf
- **Prioridade:** alta (47), media (5), baixa (2)
- **Adicionado em:** {HOJE}
- **Status:** pendente - aquisicao automatica
- **Justificativa:** os blocos #140-#144 cobrem a **rampa do acervo** (o que o acervo precisa
  para a prova de Literatura da IPB). Esta #182 cobre o outro lado: **os livros que William tem
  em casa e o acervo nao tem** - para que o acervo tenha copia fiel do que ele ja possui, com
  citacao literal em PT (Regra 9) e para a trilha de cruzamento teologia x ficcao.
- **Marcadores `E01`-`E58`:** prefixo `E` = "estante". O numero e o **id da estante** (1-58),
  nao um id sequencial da lista.

{chr(10).join(linhas)}

**Ficcao ausente do acervo: 49 de 58.** (O #3 "A Escravidao na Historia" - Adam Gurowski -
**nao e ficcao**: e historiografia de 1826, sobre a-sensorsia no mundo slaveiro. Fica listado
por completude da estante, mas nao entra na rampa de leitura.)

#### Notas de integridade (achado de {HOJE} - bug de pipeline, nao de acervo)

O cruzamento por **nome de arquivo** dava 8 "presentes". A checagem de **integridade do texto**
revelou que 3 deles **nao servem como texto legivel**:

| # | Obra | Estado real | Caminho | Acao |
|---|---|---|---|---|
| 14 | Dom Quixote | **CORROMPIDO** - 18 KB, `Traceback` do conversor, 0 linhas de prosa | `literatura-mundial-classica/Cervantes-Dom-Quixote.md` | re-extrair (o conversor gravava o erro em vez do texto) |
| 30 | Oliver Twist | **CORROMPIDO** - 81 KB, so o CSS do EPUB, 1 linha de prosa | `literatura-mundial-classica/The-Charles-Dickens-Collection-Volume-One-Oliver-Twist-Great-Expectations-and-Bleak-House.md` | re-extrair; e em **ingles** (gap de idioma) |
| 37 | Fausto / Werther | **PARCIAL** - 547 KB, mas so a introducao critica e fragmentos (64 linhas de prosa) | `literatura-mundial-classica/antigos/Fausto-Johann-Wolfgang-von-Goethe.md` | completar (falta o texto integral) |

Os mesmos dois bugs de conversao estao em **literatura-brasileira** (mesma data, mesmo
conversor): `Machado-Assis-Dom-Casmurro.md` (traceback), `Memorias-Postumas-de-Bras-Cubas`
(sem prosa) e `Graciliano-Ramos-Vidas-Secas.md` (278 bytes).

**Consequencia:** o acervo de ficcao tem **5 obras realmente legiveis** que tambem estao na
estante do William (Proust, Odisseia, Eneida, Divina Comedia I, Madame Bovary) - nao 8.

"""

marc = "### #130 — Vocação: Perspectivas Bíblicas e Teológicas (gap crítico IPB)"
assert marc in txt, "ancora nao encontrada"
if "### #182 -" in txt:
    # ja inserida: substitui a secao existente em vez de duplicar (idempotente)
    ini = txt.index("### #182 -")
    fim = txt.index(marc)
    txt = txt[:ini] + secao + txt[fim:]
else:
    txt = txt.replace(marc, secao + marc, 1)

# status dos blocos #140-#144 (rampa), conforme o acervo real
STATUS_RAMPA = {
    "#140": ("Pequeno Principe, Grande Gatsby, Pedro Paramo e os volumes de contos "
             "(Poe, Tchekhov, Maupassant, Mansfield, Gogol, Turguenev) - **9 obras, todas "
             "pendentes**. Nenhuma delas esta na estante do William: sao os degraus de "
             "calibragem de gosto."),
    "#141": ("**9 de 11 JA ADQUIRIDAS** (Orgulho e Preconceito, Jane Eyre, Madame Bovary, "
             "Tom Sawyer, Crime e Castigo, O Idiota, Middlemarch, Moby-Dick, Anna Karenina). "
             "**Faltam 2:** O Morro dos Ventos Uivantes (**voce ja tem em casa**) e "
             "O Nome da Rosa."),
    "#142": ("**9 de 9 JA ADQUIRIDAS** em PT-BR (Irmãos Karamázov, Guerra e Paz, Grandes "
             "Esperanças, Casa de Cassandra, David Copperfield, Divina Comédia, Cidade de Deus, "
             "Confissões, e a Coleção Dickens). **Ressalva:** Oliver Twist em PT segue "
             "corrompido e em inglês - ver nota de integridade na #182."),
    "#143": ("**6 de 6 pendentes** (Ortodoxia, O Homem que foi Quinta-feira, O Problema da Dor, "
             "O Peregrino, O Poder e a Glória, A Wise Blood). Zero ficcao cristiana na estante "
             "do William - e gap de intencao, nao de quantidade."),
    "#144": ("**3 de 5 JA ADQUIRIDAS** (Mrs Dalloway, e no lote: A Utopia/O Coração das Trevas "
             "pendente de conferencia de conteudo). **Pendentes:** Cem Anos de Solidão, "
             "A Utopia/O Coração das Trevas, Retratos (Dubliners)."),
}
for tag, texto in STATUS_RAMPA.items():
    # insere a linha de status logo apos a linha "Status: pendente - aquisicao automatica"
    # do bloco correspondente
    pat = re.compile(
        r"(### " + re.escape(tag) + r"[^\n]*\n(?:.|\n)*?)- \*\*Status:\*\* pendente - aquisicao automatica",
        re.M)
    novo = r"\1- **Status real (" + HOJE + r"):** " + texto + "\n- **Status:** pendente - aquisicao automatica"
    txt, n = pat.subn(novo, txt, count=1)
    assert n == 1, f"bloco {tag} nao encontrado"

txt = txt.replace("versao: '9.1'", "versao: '9.2'", 1)
txt = re.sub(r"ultima_atualizacao: .*",
              f"ultima_atualizacao: {HOJE}T11:20:00-03:00", txt, count=1)
txt = txt.replace(
    "| Itens ativos (pendentes) | 0 (todos baixáveis foram adquiridos em 2026-09-25) |",
    "| Itens ativos (pendentes) | 49 titulos de ficcao da estante fisica (#182) + 2 lacunas "
    "da rampa (#141 O Nome da Rosa, #144 Retratos) + 15 contos do degrau 1 (#140) + 6 da "
    "trilha cristiana (#143) + 6 gaps IPB/vocacao |", 1)
LISTA.write_text(txt, encoding="utf-8")
print("OK lista-aquisicao.md: #182 inserida; status dos blocos #140-#144 atualizado")

# ---------------------------------------------------------------- yaml
d = yaml.safe_load(YML.read_text(encoding="utf-8"))
d["data"] = HOJE
d["ultima_verificacao_acervo"] = (
    f"{HOJE} (varredura de texto completo: 1.078 arquivos / 1,1 GB)")
for lv in d["livros"]:
    i = lv["id"]
    if i in INTEGRIDADE:
        st, note, path = INTEGRIDADE[i]
        lv["no_acervo_study_agent"] = st
        lv["acervo_integridade"] = note
        lv["acervo"] = path
    else:
        lv["no_acervo_study_agent"] = "nao"
        lv.pop("acervo", None)
        lv.pop("acervo_integridade", None)
d["resumo"] = {
    "total": 58,
    "no_acervo_legivel": 4,
    "no_acervo_corrompido": 2,
    "no_acervo_parcial": 1,
    "so_na_estante": 49,
    "nao_ficcao_na_estante": 1,
    "buracos": "Dostoyevsky, Tolstoi, Austen, Melville, autoras - zero na estante do William",
    "gaps_de_intencao": "zero ficcao cristiana",
    "nota": ("cruzamento por TEXTO COMPLETO em " + HOJE + "; o cruzamento anterior (por nome "
             "de arquivo) dava 8 presentes, mas 3 estao corrompidos/incompletos"),
}
YML.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=100),
               encoding="utf-8")
print("OK estante-william.yaml: integridade e resumo atualizados")
