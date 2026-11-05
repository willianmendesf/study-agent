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
    ("A Utopia", "Joseph Conrad", "media", "anglo-saxoes",
     "Under Western Eyes", ["literatura", "romance", "anglo-saxoes"], 1911),
    ("O Coração das Trevas", "Joseph Conrad", "media", "anglo-saxoes",
     "Heart of Darkness", ["literatura", "romance", "canon-literario", "ingles"], 1899),
    ("Retratos", "James Joyce", "media", "anglo-saxoes",
     "Dubliners", ["literatura", "conto", "modernismo", "ingles"], 1914),
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
    ("Sangue Bom", "Flannery O'Connor", "media", "ingles",
     "Good Country People", ["literatura", "ficcao-crista", "ingles"], 1955),
    # --- gap de idioma: classicos do acervo so em ingles ---
    ("Oliver Twist", "Charles Dickens", "alta", "anglo-saxoes",
     "Oliver Twist", ["literatura", "romance", "canon-literario", "ingles", "gap-idioma"], 1838),
    ("Uma História de Duas Cidades", "Charles Dickens", "media", "anglo-saxoes",
     "A Tale of Two Cities", ["literatura", "romance", "canon-literario", "ingles"], 1859),
    # --- autores com ZERO na estante: buracos de intencao ---
    ("A Casa dos Espelhos", "Virginia Woolf", "media", "anglo-saxoes",
     "A Room of One's Own", ["literatura", "ensayo", "ingles", "feminismo"], 1929),
    ("Middlemarch", "George Eliot", "media", "anglo-saxoes",
     "Middlemarch", ["literatura", "romance", "canon-literario", "ingles"], 1871),
    ("Beloved", "Toni Morrison", "media", "anglo-saxoes",
     "Beloved", ["literatura", "romance", "ingles", "feminismo"], 1987),
    ("Se o Mundo Existisse", "Italo Calvino", "media", "italiano",
     "Se il mondo esistesse", ["literatura", "conto", "modernismo", "italiano"], 1983),
]

# ---------------------------------------------------------------------------
def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def esc(s):
    """Escapa para YAML de forma segura (aspas simples, como o resto do repo)."""
    return "'" + str(s).replace("'", "''") + "'"


def main():
    import yaml
    est = yaml.safe_load(ESTANTE.read_text(encoding="utf-8"))
    itens = []
    vistos = set()

    def add(tit, aut, prio, sub, ten, tags, ano, origem, nota=""):
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
