#!/usr/bin/env python3
"""v5 FINAL: 1 eixo de TRILHA (sempre 1) + 1 eixo opcional de LIVRO/ASSUNTO.

INSIGHT (v5): o TITULO do memo ja diz a forma ("AULA 20", "Devocional 13",
"Gabarito Quiz M1", "Plano de leitura"). Taggear por forma e redundante com o
titulo. O que o titulo NAO diz e a TRILHA (a que assunto pertence) — ai esta
o ganho real de navegar no Memos.

Prioridade de classificacao da trilha:
  1. tag antiga serie/ (a mais especifica, ja existe)
  2. tag antiga livro/ (indica estudo biblico -> exegese)
  3. regex no titulo, na ordem de especificidade
  4. fallback: classificar pela tag antiga tipo/ ou fonte/

Nao escreve nada no Memos. So le e reporta.
"""
import glob
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TRILHAS = [
    ("simulados",   "As provas em si (12 simulados) — para fazer",
     re.compile(r"^\s*📝\s*simulad|^\s*#\s*SIMULAD", re.I)),
    ("gabaritos",   "As chaves de resposta (11 gabaritos) — para conferir DEPOIS",
     re.compile(r"gabarito", re.I)),
    ("estudo-ipb",  "Material de preparacao para a prova: comite, autoavaliacao, relatorios, questoes",
     re.compile(r"\b(comit[eê]|comiss[aã]o|vocacional|autoavalia|matriz de cobertura|varia[cç][oõ]es de quest|perguntas advers|banco de perguntas|relat[oó]rio de|refer[eê]ncias|catalogo-acervo|acervo-audiovisual|mapa-progressao|fontes externas)\w*", re.I)),
    ("rampa-leitura", "Rampa de leitura de ficcao — o que ler, em que ordem",
     re.compile(r"\b(rampa|fic[cç][aã]o)\w*", re.I)),
    ("devocional",  "Devocional diario — Salmos, Proverbios, adoracao e confissao",
     re.compile(r"\b(devocional|devocion|medita|salmo \d|prov[eé]rb \d|adoracao e confissao)\w*", re.I)),
    ("aulas-portugues", "Trilha de Portugues — aula 01→20, o dia a dia",
     re.compile(r"\b(AULA \d|vogal|consoant|alfabet|silab|acentu|ortograf|ditong|tritong|hiato|fonema|fonolog|pontuac|sintaxe|redacao|lexico|mapa-m1|mapa-m2|mapa-m3|m1\.|m2\.|m3\.)\w*", re.I)),
    ("exegese",     "Estudo biblico — exegese, Etapa 0/1, contextualizacao, guias",
     re.compile(r"\b(exegese|exeg[eé]tic|leitura pr[oó]pria|di[aá]logo com os autores|etapa 0|etapa 1|hermeneu|pericope|sint[aá]tica textual|conceitual|panor[aâ]mico|contextualiza|divis[aã]o de per[ií]copes|jejum|guia de estudo|guia-bolso)\w*", re.I)),
    ("plano-estudo", "Planos, grades, roadmaps, roteiros de aula — EBD/EBDI, curriculo",
     re.compile(r"\b(plano|roadmap|grade|roteiro|trajet|sequencia|cronograma|curriculo|ebd\b|ebdi|criancas|adolescente|descoberta|esboco)\w*", re.I)),
]

# Correcoes manuais (caso a regex errou). uid -> trilha correta
CORRECOES = {
    # "Plano de Aula - Filemon (EBDI/Criancas)" e plano, nao exegese
    "GHnG6XAc7V9cn4kCB5XKpn": "plano-estudo",
    # "plano-leitura-anual-2026-2027" e plano de leitura, nao exegese
    "7UnUtn5ZyJDcYUXHNYFmDL": "plano-estudo",
    # "Plano de curadoria do Memos" ja foi APAGADO (so aparece no backup antigo)
    "oUAJYc2qUnt9YdyBcsExhc": "plano-estudo",
}

# tag antiga tipo/ -> trilha (fallback)
TIPO2TRILHA = {
    "plano": "plano-estudo", "aula": "aulas-portugues", "nota": "exegese",
    "resumo": "exegese", "guia": "exegese", "indice": "plano-estudo",
    "mapa": "plano-estudo", "ficha": "exegese", "exegese": "exegese",
    "devocional": "devocional", "simulado": "simulados", "gabarito": "gabaritos",
    "exercicio": "estudo-ipb", "relatorio": "estudo-ipb", "transcricao": "exegese",
}


def main():
    bkp = sorted(glob.glob(str(ROOT / "data" / "perfil" / "bibliotecario" / "backups-memos" / "memos-*.json")))[-1]
    todos = json.load(open(bkp, encoding="utf-8"))
    MEU = "users/willianmendesf"
    meus = [m for m in todos if (m.get("creator") or "") == MEU]
    print("fonte:", bkp.split("/")[-1], "| memos do Study-Agent:", len(meus))
    print()

    recs = []
    for m in meus:
        c = m.get("content") or ""
        ls = [l.strip() for l in c.splitlines() if l.strip()]
        titulo = " ".join(ls[:3])[:600]
        tags = m.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        tset = set(tags)

        trilha = None
        fonte_regra = ""

        # 1. regex especifico (simulados/gabaritos primeiro)
        for nome, desc, rx in TRILHAS:
            if rx.search(titulo):
                trilha, fonte_regra = nome, "regex-titulo"
                break

        # 2. tag livro/ -> estudo biblico -> exegese (se ainda nao classificado)
        if trilha is None and any(t.startswith("livro/") for t in tset):
            trilha, fonte_regra = "exegese", "tag livro/"

        # 3. tag serie/
        if trilha is None:
            for t in sorted(tset):
                if t.startswith("serie/"):
                    if "portugues" in t or re.search(r"m[123]\.", t):
                        trilha, fonte_regra = "aulas-portugues", "tag serie/"
                    elif "devocional" in t:
                        trilha, fonte_regra = "devocional", "tag serie/"
                    break

        # 4. fallback pela tag tipo/
        if trilha is None:
            for t in sorted(tset):
                if t.startswith("tipo/"):
                    trilha = TIPO2TRILHA.get(t.split("/", 1)[1])
                    fonte_regra = "tag tipo/"
                    break

        # 5. fallback por fonte/
        if trilha is None:
            if any("ipb" in t or "seminario" in t or "ebd" in t for t in tset):
                trilha, fonte_regra = "estudo-ipb", "tag fonte/"

        recs.append({
            "uid": m["name"].split("/")[-1],
            "titulo": ls[0][:110] if ls else "(vazio)",
            "trilha": trilha or "SEM-CASA",
            "regra": fonte_regra or "NENHUMA",
            "tags_atuais": tags,
        })

    # aplica correcoes manuais
    for r in recs:
        if r["uid"] in CORRECOES:
            r["trilha"] = CORRECOES[r["uid"]]
            r["regra"] = "correcao-manual"

    cnt = Counter(r["trilha"] for r in recs)
    print("=== EIXO 1 — TRILHA (sempre 1) ===")
    for nome, desc, _ in TRILHAS:
        n = cnt.get(nome, 0)
        util = "FILTRA BEM" if n <= 30 else "GRANDE"
        print(f"  {n:4d}  #{nome:16s} {util:11s} {desc}")
    print(f"  {cnt.get('SEM-CASA',0):4d}  #SEM-CASA")
    print()
    print("=== cobertura ===")
    print(f"  classificados: {len(meus) - cnt.get('SEM-CASA',0)}/{len(meus)} "
          f"({100*(len(meus)-cnt.get('SEM-CASA',0))//len(meus)}%)")
    print(f"  tags distintas: {len([t for t in cnt if t != 'SEM-CASA'])}")
    print()
    if cnt.get("SEM-CASA"):
        print("=== SEM-CASA (ainda) ===")
        for r in recs:
            if r["trilha"] == "SEM-CASA":
                print(f"  {r['uid']} | {r['titulo'][:74]}")
    print()
    print("=== contagem por regra (de onde veio a classificacao) ===")
    for k, v in Counter(r["regra"] for r in recs).most_common():
        print(f"  {v:4d}  {k}")
    print()
    print("=== sample de cada trilha ===")
    g = defaultdict(list)
    for r in recs:
        g[r["trilha"]].append(r)
    for nome, _, _ in TRILHAS:
        print(f"  -- #{nome}")
        for r in g.get(nome, [])[:3]:
            print(f"       {r['titulo'][:72]}")

    out = ROOT / "data" / "estudos" / "notas" / "memos-curadoria" / "mapeamento-tags-v5-final.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("gravado:", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
