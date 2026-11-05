#!/usr/bin/env python3
"""Re-validacao v2: uma taxonomia que responde as perguntas que o William FAZ.

O problema da v1 (6 tags por forma do documento): a aula de Portugues e o plano
de leitura da rampa caem no mesmo balde (#plano). O gabarito e a prova caem no
mesmo balde (#simulado). Isso nao ajuda a navegar.

v2: tags por ASSUNTO/TEMA (o que eu estudo) + 1 tag de ESTADO (o que eu faco com
isso agora) + tags especificas de materia.

Nao escreve nada no Memos. So le e reporta.
"""
import importlib.util
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def carregar_curador():
    spec = importlib.util.spec_from_file_location("cur", ROOT / "scripts" / "curador-memos.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# v2: ASSUNTO (sempre 1) + ESTADO (opcional, 1) + MATERIA (opcional)
# ---------------------------------------------------------------------------
# ASSUNTO: o que eu estudo (independe da forma do documento)
ASSUNTO = {
    "teologia":     re.compile(r"\b(devocional|exegese|hermeneu|teolog|pericope|salmo|prov[eé]rb|jo[aã]o|ef[eé]sios|filemon|tito|romanos|1\s*jo[aã]o|jejum|oracao|adoracao|confissao|reforma|biblic)\w*", re.I),
    "portugues":    re.compile(r"\b(aula|vogal|consoant|alfabet|silab|acentu|ortograf|ditong|tritong|hiato|portugu|fonema|fonolog|pontuac|sintaxe|redacao|lexico|classes? de palavras)\w*", re.I),
    "literatura":   re.compile(r"\b(rampa|literatur|romance|conto|novela|dostoiev|anatole|thackeray|proust|austen|dickens|melville|orwell|twain|tolstoi|shelley|flaubert|wolf|nostradamus|fiction)\w*", re.I),
    "curriculo":    re.compile(r"\b(ipb|candidatura|seminario|ebd|ebdi|criancas|adolescente|comite|vocacional|comissao|curriculo|simulado|quiz|prova)\w*", re.I),
}

# ESTADO: o que eu faco com isso AGORA (a tag que ele realmente quer)
ESTADO = {
    "plano":     re.compile(r"\b(plano|roadmap|grade|rampa|trajet|roteiro|sequencia|passo a passo|cronograma|aula \d|proxim[ao] passos?|onde estou|agenda)\b", re.I),
    "resumo":    re.compile(r"\b(resumo|sintese|introdu[cç][aã]o|contextualiza|panoram|vis[aã]o geral|conceitual|s[aã]ntese|o que importa|em poucas linhas)\b", re.I),
    "ficha":     re.compile(r"\b(ficha|guia|bolso|perguntas|banco de|matriz|varia[cç][oõ]es|refer[eê]ncias|acompanhamento|roteiro de aula|o que olhar|observar)\b", re.I),
    "exegese":   re.compile(r"\b(exegese|exeg[eé]tic|sint[aá]tica textual|leitura pr[oó]pria|di[aá]logo com os autores|etapa 0|etapa 1|an[aá]lise do texto)\b", re.I),
    "devocional": re.compile(r"\b(devocional|devocion|medita|salmo \d|prov[eé]rb \d|adoracao e confissao)\b", re.I),
    "simulado":  re.compile(r"\b(simulado|quiz|gabarito|treino|treinar|simula[cç][aã]o de entrevista|bateria de quest|perguntas de comit)\w*", re.I),
}

# MATERIA (opcional): so entra se o memo for claramente sobre isso
MATERIA = {
    "ipb":    re.compile(r"\b(ipb|processo de admiss[aã]o|candidatura|conselho de comiss[aã]o|semin[aá]rios)\b", re.I),
    "leitura": re.compile(r"\b(estou lendo|lendo agora|rampa de leitura|livro atual|em andamento)\b", re.I),
}


def classificar(m):
    c = m.get("content") or ""
    linhas = [l.strip() for l in c.splitlines() if l.strip()]
    titulo = " ".join(linlines for linlines in linhas[:3])[:500]

    tags = m.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    ts = set(tags)

    # materia primeiro (mais especifico)
    materia = None
    if re.search(r"fonte/ipb-candidatura|livro/", ts and " ".join(tags) or ""):
        pass
    for nome, rx in MATERIA.items():
        if rx.search(titulo):
            materia = nome
            break

    # ASSUNTO: tag antiga (estudo/xxx) > regex
    assunto = None
    for t in tags:
        if t.startswith("estudo/"):
            assunto = t.split("/", 1)[1]
            break
    if not assunto:
        for nome, rx in ASSUNTO.items():
            if rx.search(titulo):
                assunto = nome
                break
    if not assunto:
        assunto = "geral"

    # ESTADO: tag antiga tipo/ > regex
    estado = None
    for t in tags:
        if t.startswith("tipo/"):
            chave = t.split("/", 1)[1]
            estado = {
                "plano": "plano", "aula": "plano", "nota": "resumo", "resumo": "resumo",
                "guia": "ficha", "indice": "indice", "mapa": "ficha", "ficha": "ficha",
                "exegese": "exegese", "devocional": "devocional", "simulado": "simulado",
                "gabarito": "simulado", "exercicio": "simulado", "relatorio": "relatorio",
                "transcricao": "transcricao",
            }.get(chave)
            break
    if not estado:
        for nome, rx in ESTADO.items():
            if rx.search(titulo):
                estado = nome
                break
    if not estado:
        estado = "resumo"

    return assunto, estado, materia


def main():
    cur = carregar_curador()
    cur.carregar_env()
    # Usa o backup local (mesmos dados, sem latencia da API do tailnet)
    import glob
    bkp = sorted(glob.glob(str(ROOT / "data" / "perfil" / "bibliotecario" / "backups-memos" / "memos-*.json")))[-1]
    todos = json.load(open(bkp, encoding="utf-8"))
    print("fonte:", bkp.split("/")[-1])
    MEU = "users/willianmendesf"
    meus = [m for m in todos if (m.get("creator") or "") == MEU]

    recs = []
    for m in meus:
        assunto, estado, materia = classificar(m)
        c = m.get("content") or ""
        ls = [l.strip() for l in c.splitlines() if l.strip()]
        recs.append({
            "uid": cur.uid(m),
            "titulo": ls[0][:110] if ls else "(vazio)",
            "assunto": assunto,
            "estado": estado,
            "materia": materia,
            "tags_atuais": m.get("tags") or [],
        })

    cnt_assunto = Counter(r["assunto"] for r in recs)
    cnt_estado = Counter(r["estado"] for r in recs)
    cnt_mat = Counter(r["materia"] for r in recs)

    print(f"memos do Study-Agent: {len(recs)}")
    print()
    print("=== EIXO 1 — ASSUNTO (sempre 1) ===")
    for t, n in cnt_assunto.most_common():
        print(f"  {n:4d}  #{t}")
    print()
    print("=== EIXO 2 — ESTADO (sempre 1) ===")
    for t, n in cnt_estado.most_common():
        print(f"  {n:4d}  #{t}")
    print()
    print("=== EIXO 3 — MATERIA (opcional) ===")
    for t, n in cnt_mat.most_common():
        print(f"  {n:4d}  #{t}")
    print()
    print("=== SAMPLE por combinacao (pra ver se faz sentido) ===")
    combo = defaultdict(list)
    for r in recs:
        combo[(r["assunto"], r["estado"])].append(r)
    for k in sorted(combo, key=lambda k: -len(combo[k])):
        print(f"  {k[0]:12s} + {k[1]:12s} = {len(combo[k]):3d}")
        for r in combo[k][:2]:
            print(f"       - {r['titulo'][:78]}")

    out = ROOT / "data" / "estudos" / "notas" / "memos-curadoria" / "mapeamento-tags-v2.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("gravado:", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
