#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
catalogo-compras.py — montador do CATALOGO DE COMPRAS de livros.

Por que existe:
  Quando uma obra necessaria nao esta no acervo E o z-library nao devolve
  (busca feita, sem resultado), o proximo passo e COMPRAR em PT-BR.
  Este script monta esse catalogo: para cada obra do gap, busca links REAIS
  em Amazon (prioridade), Mercado Livre, Shopee, Saraiva, Cultura, Estantica.

Regras dureis (AGENTS.md + regra de escrita externa):
  - Link so entra no catalogo se veio de uma BUSCA REAL (SearXNG). Nada inventado.
  - O script NUNCA compra, NUNCA clica em "comprar", NUNCA faz pedido.
  - Status inicial e sempre 'a_comprar' (quando ha link) ou 'sem_link'.
    O status so muda por acao manual do William ou por ele dizer que comprou.
  - Escrita externa (comprar) exige APROVACAO EXPLICITA, turno a turno.

Uso:
  python3 scripts/catalogo-compras.py --gerar            # gera catalogo (SearXNG)
  python3 scripts/catalogo-compras.py --gerar --limit 20
  python3 scripts/catalogo-compras.py --relatorio        # so o estado atual
"""
import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
GAP = Path("/tmp/gap-canonicos.json")
YAML_OUT = DATA / "perfil/bibliotecario/catalogo-compras.yaml"
MD_OUT = DATA / "biblioteca/catalogo-compras.md"
SEARXNG = "http://192.168.15.41:82/search"

# Prioridade de loja: Amazon primeiro (fisico OU digital/Kindle).
LOJAS = [
    ("amazon", "Amazon.com.br", [
        r"amazon\.com\.br/.*-dp/([A-Z0-9]{10})",
        r"amazon\.com\.br/.*/dp/([A-Z0-9]{10})",
        r"amazon\.com\.br/([^/]+)/(?:dp|gp/product)/",
    ]),
    ("mercadolivre", "Mercado Livre", [
        r"mercadolivre\.com\.br/([^/]+)/p/([A-Z0-9]+)",
        r"mercadolivre\.com\.br/([^/]+)-p-([A-Z0-9]+)",
    ]),
    ("shopee", "Shopee", [
        r"shopee\.com\.br/[^/]+/[^/]+/[^/]+/(\d+\.\d+)",
    ]),
    ("saraiva", "Saraiva", [
        r"saraiva\.com\.br/([^/]+)/([^/]+)-\d+",
    ]),
    ("cultura", "Cultura", [
        r"cultura\.com\.br/([^/]+)/([^/]+)-\d+",
    ]),
    ("estantica", "Estantica", [
        r"estantica\.com\.br/([^/]+)/([^/]+)-\d+",
    ]),
]

PALAVRAS_PARADA = {
    "de", "da", "do", "das", "dos", "a", "o", "e", "em", "para", "com",
    "the", "of", "and",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", s.lower())


def tokens(s: str):
    return set(t for t in norm(s).split() if t and t not in PALAVRAS_PARADA)


SUSPENSO = re.compile(r"Suspenso|demasiadas solicita|CAPTCHA|Too Many", re.I)


def searxng(query: str, limit: int = 12, lang="pt-BR", tentativas=3):
    """Busca no SearXNG local COM BACKOFF.

    Bug medido (2026-11-07): quando o engine aggregator satura (google cse
    'demasiadas solicitacoes'), a API responde HTTP 200 com `results: []` e um
    `unresponsive_engines` avisando. Sem backoff, a rodada inteira produz
    ZERO links e parece 'sem_link' — falso negativo. Aqui detectamos a
    suspensao e esperamos antes de desistir.
    """
    # ENGINE FIXO = bing.
    # Bug medido (2026-11-07): o aggregator padrao traria google cse + brave +
    # duckduckgo + wikipedia, e os 4 caem em "demasiadas solicitacoes" / CAPTCHA
    # quando a cota do IP estoura. A API responde HTTP 200 com results: [] — um
    # falso negativo silencioso que fazia a rodada marcar TUDO como sem_link.
    # O bing responde normalmente (10 resultados) mesmo com os outros caidos.
    params = urllib.parse.urlencode(
        {"format": "json", "q": query, "language": lang, "safesearch": 0,
         "engines": "bing"}
    )
    url = f"{SEARXNG}?{params}"
    espera = 8
    for tentativa in range(tentativas):
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
            res = data.get("results", []) or []
            suspensos = data.get("unresponsive_engines") or []
            if res:
                return res
            if suspensos and tentativa < tentativas - 1:
                sys.stderr.write(
                    f"[searxng suspenso, aguardando {espera}s] {query[:50]}\n")
                time.sleep(espera)
                espera *= 2
                continue
            return res
        except Exception as e:  # noqa
            sys.stderr.write(f"[searxng falhou] {query}: {e}\n")
            if tentativa < tentativas - 1:
                time.sleep(espera)
                espera *= 2
                continue
            return []
    return []


def casar(obra_toks, autor_toks, texto: str) -> float:
    """Score de aderencia do resultado ao titulo/autor procurados."""
    t = set(tokens(texto))
    if not t:
        return 0.0
    cov_titulo = len(obra_toks & t) / max(1, len(obra_toks))
    cov_autor = len(autor_toks & t) / max(1, len(autor_toks)) if autor_toks else 0.0
    return round(0.72 * cov_titulo + 0.28 * cov_autor, 3)


def classificar(url: str):
    for chave, nome, padroes in LOJAS:
        for p in padroes:
            m = re.search(p, url)
            if m:
                return chave, nome, m.group(0)
    return None


def buscar_item(item):
    titulo = item.get("titulo", "")
    autor = item.get("autor", "")
    obra_toks = tokens(titulo)
    autor_toks = tokens(autor)
    # variantes de titulo (ex.: "Morre de Ivan Illicht" -> "Morte de Ivan Ilyitch")
    variantes = item.get("variantes") or [titulo]
    consultas = []
    for v in [titulo] + list(variantes)[:2]:
        consultas.append(f'"{v}" {autor} livro comprar')
    consultas.append(f'site:amazon.com.br "{titulo}" {autor}')

    achados = {}
    for q in consultas:
        for r in searxng(q):
            url = r.get("url") or ""
            if not url:
                continue
            c = classificar(url)
            if not c:
                continue
            chave, nome, _ = c
            score = casar(obra_toks, autor_toks, (r.get("title") or "") + " " + (r.get("content") or ""))
            if score < 0.34:
                continue
            atual = achados.get(chave)
            if atual is None or score > atual["score"]:
                achados[chave] = {
                    "loja": chave,
                    "loja_nome": nome,
                    "url": url,
                    "titulo_loja": (r.get("title") or "").strip(),
                    "score": score,
                    "snippet": re.sub(r"\s+", " ", (r.get("content") or ""))[:220],
                }
        if achados:
            break
    return item, achados


def carregar_gap():
    if not GAP.exists():
        raise SystemExit(f"gap nao encontrado: {GAP}")
    return json.loads(GAP.read_text(encoding="utf-8"))


def filtrar(gap, limite=None):
    """Prioridade: obras citadas em 2+ listas (gap canonico) + prioridade maxima."""
    sel = [g for g in gap if (g.get("n_listas") or 0) >= 2]
    sel.sort(key=lambda g: (-(g.get("n_listas") or 0), -(g.get("prioridade") or 0)))
    return sel[:limite] if limite else sel


def carregar_existentes():
    """Links ja encontrados — para retomar sem perder trabalho."""
    if not YAML_OUT.exists():
        return {}
    try:
        import yaml
        doc = yaml.safe_load(YAML_OUT.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    out = {}
    for o in doc.get("obras", []) or []:
        if o.get("lojas"):
            out[(o.get("titulo"), o.get("autor"))] = o["lojas"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gerar", action="store_true")
    ap.add_argument("--relatorio", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--min-listas", type=int, default=2)
    ap.add_argument("--retomar", action="store_true",
                    help="nao refaz a busca de obras que ja tem link (aguenta o rate limit)")
    ap.add_argument("--pausa", type=float, default=1.5,
                    help="segundos de pausa entre buscas (evita 'google cse suspenso')")
    args = ap.parse_args()

    if not args.gerar and not args.relatorio:
        ap.print_help()
        return

    if args.relatorio:
        if YAML_OUT.exists():
            print(YAML_OUT.read_text(encoding="utf-8")[:4000])
        else:
            print("catalogo ainda nao gerado")
        return

    gap = carregar_gap()
    sel = [g for g in gap if (g.get("n_listas") or 0) >= args.min_listas]
    sel.sort(key=lambda g: (-(g.get("n_listas") or 0), -(g.get("prioridade") or 0)))
    if args.limit:
        sel = sel[: args.limit]
    existentes = carregar_existentes() if args.retomar else {}
    if args.retomar and existentes:
        print(f"[catalogo-compras] retomando: {len(existentes)} obras ja tem link", file=sys.stderr)

    import time
    resultados = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for item, achados in ex.map(buscar_item, sel):
            chave = (item.get("titulo"), item.get("autor"))
            if not achados and chave in existentes:
                achados = {l["loja"]: l for l in existentes[chave]}
            resultados.append((item, achados))
            status = "OK" if achados else "sem_link"
            print(f"  {status:9} {item.get('titulo')} — {item.get('autor')}", file=sys.stderr)
            time.sleep(args.pausa)

    linhas = []
    for item, achados in resultados:
        entrada = {
            "titulo": item.get("titulo"),
            "autor": item.get("autor") or None,
            "genero": item.get("genero"),
            "n_listas": item.get("n_listas"),
            "prioridade": item.get("prioridade"),
            "variantes": item.get("variantes") or [],
            "status": "a_comprar" if achados else "sem_link",
            "lojas": [],
        }
        ordem = {k: i for i, (k, _, _) in enumerate(LOJAS)}
        for chave, v in sorted(achados.items(), key=lambda kv: ordem.get(kv[0], 99)):
            entrada["lojas"].append({
                "loja": v["loja"],
                "loja_nome": v["loja_nome"],
                "url": v["url"],
                "titulo_anuncio": v["titulo_loja"],
                "score_aderencia": v["score"],
            })
        linhas.append(entrada)

    YAML_OUT.parent.mkdir(parents=True, exist_ok=True)
    import yaml
    doc = {
        "tipo": "catalogo-compras",
        "descricao": (
            "Obras necessarias que o z-library NAO devolveu e que devem ser COMPRADAS "
            "em PT-BR. Prioridade de loja: Amazon (fisico ou digital/Kindle), depois "
            "Mercado Livre, Shopee, Saraiva, Cultura, Estantica. O catalogo NAO compra: "
            "ele apenas cataloga o link e o status. Status possiveis: "
            "a_comprar | em_compra | comprado | recebido | sem_link | descartado."
        ),
        "data": "2026-11-07",
        "gerado_por": "scripts/catalogo-compras.py",
        "fonte_gap": "data/estudos/notas/ficcao-rampa-leitura/15-rampa-v4-canonicos.md",
        "regra_escrita_externa": (
            "COMPRAR exige aprovacao explicita do William, turno a turno. "
            "O agente cataloga e sugere; nao executa compra."
        ),
        "total": len(linhas),
        "com_link": sum(1 for l in linhas if l["status"] == "a_comprar"),
        "sem_link": sum(1 for l in linhas if l["status"] == "sem_link"),
        "obras": linhas,
    }
    YAML_OUT.write_text(
        "# catalogo-compras.yaml — GERADO por scripts/catalogo-compras.py — nao editar a mao\n"
        + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=4096),
        encoding="utf-8",
    )
    print(f"[catalogo-compras] gravado: {YAML_OUT}  ({doc['com_link']} com link / {doc['sem_link']} sem)", file=sys.stderr)


if __name__ == "__main__":
    main()
