#!/usr/bin/env python3
"""v4: 1 eixo de TRILHA, em ordem de especificidade, medindo cobertura real.

INSIGHT: o titulo do memo JA diz o que ele e ("AULA 20 - ...", "Devocional 13
- ...", "Gabarito Quiz M1 - ...", "Plano de leitura"). A tag tipo/ e 100%
redundante com o titulo. O que o titulo NAO diz e a TRILHA (a que assunto
pertence) — e ai esta o ganho real de navegar.

Nao escreve nada no Memos. So le e reporta.
"""
import glob
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ORDEM = prioridade. O primeiro que casar vence.
TRILHAS = [
    ("prova-ipb", "Prova da IPB — simulados, gabaritos, questoes, relatorios, comite",
     re.compile(r"\b(simulad|gabarito|quiz|relat[oó]rio|comit[eê]|comiss[aã]o|vocacional|autoavalia|matriz de cobertura|varia[cç][oõ]es de quest|perguntas advers|banco de perguntas|quest[oõ]es)\w*", re.I)),
    ("rampa-leitura", "Rampa de leitura de ficcao — o que ler, em que ordem",
     re.compile(r"\b(rampa|fic[cç][aã]o|literatur|romance|conto|novela)\w*", re.I)),
    ("devocional", "Devocional diario — Salmos, Proverbios, adoracao e confissao",
     re.compile(r"\b(devocional|devocion|medita|salmo \d|prov[eé]rb \d|adoracao e confissao)\w*", re.I)),
    ("exegese", "Exegese biblica — Etapa 0 (leitura propria) e Etapa 1 (dialogo com autores)",
     re.compile(r"\b(exegese|exeg[eé]tic|leitura pr[oó]pria|di[aá]logo com os autores|etapa 0|etapa 1|hermeneu|pericope|sint[aá]tica textual)\w*", re.I)),
    ("aulas-portugues", "Aulas de Portugues — trilha diaria, aula 01→20",
     re.compile(r"\b(AULA \d|vogal|consoant|alfabet|silab|acentu|ortograf|ditong|tritong|hiato|fonema|fonolog|pontuac|sintaxe|redacao|lexico|m1\.|m2\.|m3\.)\w*", re.I)),
    ("plano-estudo", "Planos, grades, roadmaps, roteiros — EBD/EBDI, curriculo,发现了",
     re.compile(r"\b(plano|roadmap|grade|roteiro|trajet|sequencia|cronograma|curriculo|ebd\b|ebdi|criancas|adolescente|descoberta)\w*", re.I)),
    ("guia-biblio", "Guias e materiais de estudo biblico — guia de estudo, guia de bolso",
     re.compile(r"\b(guia|bolso|biblia|manual do candidato)\w*", re.I)),
]


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
        titulo = " ".join(ls[:3])[:500]
        caminho = None
        for nome, desc, rx in TRILHAS:
            if rx.search(titulo):
                caminho = nome
                break
        recs.append({
            "uid": m["name"].split("/")[-1],
            "titulo": ls[0][:110] if ls else "(vazio)",
            "caminho": caminho or "SEM-CASA",
            "tags_atuais": m.get("tags") or [],
        })

    cnt = Counter(r["caminho"] for r in recs)
    print("=== EIXO UNICO: #trilha ===")
    for nome, desc, _ in TRILHAS:
        n = cnt.get(nome, 0)
        print(f"  {n:4d}  #{nome:16s} {desc}")
    print(f"  {cnt.get('SEM-CASA',0):4d}  #SEM-CASA")
    print()

    print("=== os SEM-CASA (decidem se a taxonomia fecha) ===")
    for r in recs:
        if r["caminho"] == "SEM-CASA":
            print(f"  {r['uid']} | {r['titulo'][:78]}")
            print(f"       tags atuais: {','.join(r['tags_atuais'])}")
    print()

    # Useful: quantos memos vao ficar em cada balde (o tamanho do balde = o filtro)
    print("=== BALDES: o filtro e util se o balde for pequeno ===")
    for nome, desc, _ in TRILHAS:
        n = cnt.get(nome, 0)
        util = "FILTRA BEM" if n <= 30 else "GRANDE DEMAIS" if n <= 60 else "NAO FILTRA"
        print(f"  {n:4d}  #{nome:16s} {util}")
    print()
    print(f"total de tags distintas na proposta: {len([t for t in cnt if t != 'SEM-CASA'])}")

    out = ROOT / "data" / "estudos" / "notas" / "memos-curadoria" / "mapeamento-tags-v4.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
    print("gravado:", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
