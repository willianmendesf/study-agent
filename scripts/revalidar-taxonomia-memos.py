#!/usr/bin/env python3
"""Re-validacao da taxonomia do Memos: as 6 tags proposals cobrem os 142 memos?

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


# --- as 6 tags propostas ---
PROPOSTAS = ["plano", "resumo", "ficha", "exegese", "devocional", "simulado"]

# --- mapeamento honesto: tag atual -> tag proposta ---
# (o que hoje esta no eixo tipo/ e para onde cada uma vai)
DE_TIPO = {
    "plano": "plano",
    "resumo": "resumo",
    "ficha": "ficha",
    "guia": "ficha",
    "nota": "resumo",
    "indice": "ficha",
    "mapa": "ficha",
    "exegese": "exegese",
    "devocional": "devocional",
    "aula": "plano",
    "simulado": "simulado",
    "gabarito": "simulado",
    "exercicio": "simulado",
    "relatorio": "resumo",
    "transcricao": "resumo",
}

# --- deteccao por conteudo quando a tag nao basta ---
RE_TITULO = [
    ("simulado", re.compile(r"simulado|gabarito|quiz|prova de[a-z]|\bM\d+\b", re.I)),
    ("devocional", re.compile(r"devocional|devocion|medita|adoracao|confissao|salmo \d|provérbio|proverbio", re.I)),
    ("exegese", re.compile(r"exegese|exegétic|análise sintática|leitura própria|diálogo com os autores|etapa 0|etapa 1", re.I)),
    ("plano", re.compile(r"plano|roadmap|grade|rampa|trajet|roteiro|cronograma|sequência|passo a passo", re.I)),
    ("ficha", re.compile(r"guia|ficha|bolso|perguntas|banco de|matriz|variações|referências|acompanhamento", re.I)),
    ("resumo", re.compile(r"resumo|síntese|introdução|contextualiza|visão geral|panorâmico|panoramica|estudo aprofundado", re.I)),
]


def tag_do_memo(m):
    """Devolve (tag_proposta, confianca, motivo)."""
    tags = m.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    c = m.get("content") or ""
    linhas = [l.strip() for l in c.splitlines() if l.strip()]
    titulo = " ".join(linhas[:3])[:400]

    # 1. tag antiga do eixo tipo/ (prioridade: ja existe, nao inventa)
    for t in tags:
        if t.startswith("tipo/"):
            chave = t.split("/", 1)[1]
            if chave in DE_TIPO:
                return DE_TIPO[chave], "alta", f"tag antiga {t}"

    # 2. emoji de prefixo (memos antigos com emoji no titulo)
    if re.match(r"^(📋|📖|📓|🔍|🙏|📝|📊|🗺️|📚|🗒️)", titulo):
        mapa = {"📋": "plano", "📖": "ficha", "📓": "resumo", "🔍": "exegese",
                "🙏": "devocional", "📝": "simulado", "📊": "resumo",
                "🗺️": "ficha", "📚": "ficha"}
        return mapa[titulo[0]], "media", "emoji de prefixo"

    # 3. regex no titulo
    for tag, rx in RE_TITULO:
        if rx.search(titulo):
            return tag, "media", "regex no titulo"

    return None, "baixa", "SEM CLASSIFICACAO"


def main():
    cur = carregar_curador()
    cur.carregar_env()
    todos = cur.listar()
    MEU = "users/willianmendesf"
    meus = [m for m in todos if (m.get("creator") or "") == MEU]

    linhas = []
    nao_classificados = []
    for m in meus:
        tag, conf, motivo = tag_do_memo(m)
        c = m.get("content") or ""
        ls = [l.strip() for l in c.splitlines() if l.strip()]
        titulo = ls[0][:100] if ls else "(vazio)"
        rec = {
            "uid": cur.uid(m),
            "titulo": titulo,
            "tag_proposta": tag,
            "confianca": conf,
            "motivo": motivo,
            "tags_atuais": m.get("tags") or [],
        }
        linhas.append(rec)
        if tag is None:
            nao_classificados.append(rec)

    cont = Counter(r["tag_proposta"] for r in linhas)
    conf = Counter(r["confianca"] for r in linhas)

    print(f"memos do Study-Agent: {len(linhas)}")
    print(f"tags distintas HOJE: {len({t for r in linhas for t in r['tags_atuais']})}")
    print()
    print("=== distribuicao nas 6 tags propostas ===")
    for t in PROPOSTAS:
        print(f"  {cont.get(t,0):4d}  #{t}")
    print(f"  {cont.get(None,0):4d}  SEM CLASSIFICACAO")
    print()
    print("=== confianca da classificacao ===")
    for k, v in conf.items():
        print(f"  {k}: {v}")
    print()
    print("=== os que NAO cabem em 6 tags (precisam de rotulo novo) ===")
    for r in nao_classificados:
        print(f"  [{r['confianca']}] {r['uid']}")
        print(f"       {r['titulo']}")
        print(f"       tags atuais: {','.join(r['tags_atuais'])}")
    print()
    print("=== quais tipos antigos somem (e quantos) ===")
    cnt_tipo = Counter()
    for r in linhas:
        for t in r["tags_atuais"]:
            if t.startswith("tipo/"):
                cnt_tipo[t] += 1
    for t, n in sorted(cnt_tipo.items(), key=lambda x: -x[1]):
        destino = DE_TIPO.get(t.split("/", 1)[1], "?")
        print(f"  {n:4d}  {t:20s} -> {destino}")

    out = ROOT / "data" / "estudos" / "notas" / "memos-curadoria" / "mapeamento-tags-6-propostas.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(linhas, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("mapeamento completo gravado em:", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
