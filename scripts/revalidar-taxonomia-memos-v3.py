#!/usr/bin/env python3
"""v3: taxonomia por CAMINHO DE USO (nao por forma do documento).

O problema da v1 (6 tags por forma): a AULA 20 de Portugues e o plano de
leitura da rampa caem no mesmo balde. O gabarito e a prova tambem.

O que o William realmente faz ao abrir o Memos: "onde eu parei / o que vem
depois / onde acho o material da prova". Isso e por CAMINHO (a trilha que
ele percorre), nao por forma do documento.

Nao escreve nada no Memos. So le e reporta.
"""
import glob
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Cada CAMINHO e uma trilha de estudo real do William, com o que entra nela.
CAMINHOS = {
    "portugues": (
        "Aulas de Portugues (a trilha diaria, aula 01→20)",
        re.compile(r"\b(AULA \d|portugu|vogal|consoant|alfabet|silab|acentu|ortograf|ditong|tritong|hiato|fonema|fonolog|pontuac|sintaxe|redacao|lexico|m1\.|m2\.|m3\.)\w*", re.I),
    ),
    "devocional": (
        "Devocional diario (Salmos, Proverbios, Adoracao)",
        re.compile(r"\b(devocional|devocion|medita|salmo \d|prov[eé]rb \d|adoracao e confissao)\w*", re.I),
    ),
    "exegese": (
        "Exegese biblica (Tito, Efesios, Filemon, Joao, 1Joao) — Etapa 0/1",
        re.compile(r"\b(exegese|exeg[eé]tic|leitura pr[oó]pria|di[aá]logo com os autores|etapa 0|etapa 1|hermeneu|pericope|sint[aá]tica textual)\w*", re.I),
    ),
    "simulado-ipb": (
        "Prova da IPB (simulados, gabaritos, questoes, relatorios)",
        re.compile(r"\b(simulado|quiz|gabarito|relat[oó]rio|comit[eê]|comiss[aã]o|vocacional|autoavalia|matriz de cobertura|varia[cç][oõ]es de quest|perguntas advers|banco de perguntas)\w*", re.I),
    ),
    "rampa-leitura": (
        "Rampa de leitura de ficcao (o que ler, em que ordem)",
        re.compile(r"\b(rampa|literatur|romance|conto|novela|fic[cç][aã]o)\w*", re.I),
    ),
    "plano-estudo": (
        "Planos, grades, roadmaps, roteiros de aula (EBD/EBDI, curriculo)",
        re.compile(r"\b(plano|roadmap|grade|roteiro|trajet|sequencia|cronograma|curriculo|ebd\b|ebdi|criancas|adolescente|descoberta)\w*", re.I),
    ),
    "guia-biblio": (
        "Guias e materiais de estudo biblico (guia de estudo, guia de bolso)",
        re.compile(r"\b(guia|bolso|biblia|hermeneu|manual do candidato)\w*", re.I),
    ),
    "estudo-geral": (
        "Estudos soltos sem trilha definida (filemon panoramico, jejum, etc)",
        re.compile(r".*", re.I),
    ),
}


def main():
    bkp = sorted(glob.glob(str(ROOT / "data" / "perfil" / "bibliotecario" / "backups-memos" / "memos-*.json")))[-1]
    todos = json.load(open(bkp, encoding="utf-8"))
    MEU = "users/willianmendesf"
    meus = [m for m in todos if (m.get("creator") or "") == MEU]
    print("fonte:", bkp.split("/")[-1], "| memos:", len(meus))
    print()

    recs = []
    for m in meus:
        c = m.get("content") or ""
        ls = [l.strip() for l in c.splitlines() if l.strip()]
        titulo = " ".join(ls[:2])[:400]
        tags = m.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        tset = set(tags)

        caminho = None
        # 1. tag antiga mais especifica (serie/ e livro/) tem prioridade
        for pref in ("serie/", "fonte/"):
            for t in sorted(tset):
                if t.startswith(pref):
                    caminho = "series-especifica"
        # 2. regex, na ordem de especificidade
        for nome, (desc, rx) in CAMINHOS.items():
            if rx.search(titulo):
                caminho = nome
                break
        if caminho is None:
            caminho = "estudo-geral"
        recs.append({"uid": m["name"].split("/")[-1], "titulo": ls[0][:100] if ls else "(vazio)",
                     "caminho": caminho, "tags": tags})

    cnt = Counter(r["caminho"] for r in recs)
    print("=== EIXO UNICO: #caminho (o que eu percorro) ===")
    for nome, (desc, _) in CAMINHOS.items():
        n = cnt.get(nome, 0)
        if n:
            print(f"  {n:4d}  #{nome:14s} {desc}")
    extras = {k: v for k, v in cnt.items() if k not in CAMINHOS}
    for k, v in extras.items():
        print(f"  {v:4d}  #{k}")
    print()

    # as 4 notas tecnicas (ele aprovou apagar)
    print("=== as 4 notas 'Nota tecnica' (P1 = sim, saem) ===")
    for r in recs:
        if "Nota t" in r["titulo"] and "cnica" in r["titulo"]:
            print("  ", r["uid"], "|", r["titulo"][:70])
    print()

    # sobreposicoes: quantos titulos casam em mais de um caminho
    print("=== titulos que casam em MAIS de um caminho (conflito) ===")
    amb = []
    for r in recs:
        hits = [n for n, (d, rx) in CAMINHOS.items() if n != "estudo-geral" and rx.search(r["titulo"])]
        if len(hits) > 1:
            amb.append((r["titulo"][:62], hits))
    for t, h in amb[:20]:
        print(f"  {t:64s} {h}")
    print(f"  total ambiguos: {len(amb)}")

    out = ROOT / "data" / "estudos" / "notas" / "memos-curadoria" / "mapeamento-tags-v3.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("gravado:", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
