#!/usr/bin/env python3
"""
searxng-search.py — Busca na web via SearXNG (LXC tools-searxng, 192.168.15.41:82).

Substitui/complementa web_search do picoclaw quando a busca nativa falha
ou quando você quer a perspectiva agregada de múltiplos engines (Google,
Bing, DuckDuckGo, Brave, etc. — definidos na config do próprio SearXNG).

Endpoint: http://192.168.15.41:82/search?format=json&q=...
Saída:    JSON estruturado OU texto humano (default).

Uso:
    python3 searxng-search.py "calvinismo e razão"                    # texto, 10 res
    python3 searxng-search.py "João Calvino vida" -k 5 --json         # JSON, 5 res
    python3 searxng-search.py "hermenêutica reformada" --lang pt-BR   # filtro idioma
    python3 searxng-search.py "..." --engines "google,bing"           # só engines
    python3 searxng-search.py "..." --time d                           # último dia
    python3 searxng-search.py "..." --safe 0                          # sem filtro safe

Status HTTP é impresso em stderr (linha "status: HTTP N | t Xs").
Em caso de falha, exit code 1 + mensagem em stderr.

Reuso: o helper `search_json()` aceita parâmetros e devolve o dict parseado,
pra chamar de outras skills/agents (sem reescrever a lógica de retry).
"""
from __future__ import annotations
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_URL = "http://192.168.15.41:82/search"
TIMEOUT_S = 15


def search_json(
    query: str,
    *,
    limit: int = 10,
    lang: str | None = None,
    time_range: str | None = None,  # d, w, m, y
    engines: str | None = None,
    safesearch: int = 1,             # 0 off, 1 moderado, 2 estrito
    base_url: str = DEFAULT_URL,
    timeout: int = TIMEOUT_S,
) -> dict[str, Any]:
    """Faz a busca e devolve o dict do SearXNG. Levanta RuntimeError em falha."""
    if not query.strip():
        raise ValueError("query vazia")

    params: dict[str, str] = {
        "q": query,
        "format": "json",
        "safesearch": str(safesearch),
    }
    if lang:
        params["language"] = lang
    if time_range:
        if time_range not in {"d", "w", "m", "y"}:
            raise ValueError(f"time_range inválido: {time_range!r} (use d/w/m/y)")
        params["time_range"] = time_range
    if engines:
        params["engines"] = engines

    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    t0 = time.time()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        # Retry gracioso: se 400 veio de combinação time_range + engine ruim,
        # tira o time_range e tenta de novo (limpa o resultado mas não trava).
        if e.code == 400 and time_range and "time_range" in params:
            fallback_params = {k: v for k, v in params.items() if k != "time_range"}
            fallback_url = f"{base_url}?{urllib.parse.urlencode(fallback_params)}"
            try:
                with urllib.request.urlopen(fallback_url, timeout=timeout) as resp2:
                    raw = resp2.read()
                    status = resp2.status
            except Exception as e2:  # noqa: BLE001
                raise RuntimeError(
                    f"falha HTTP em {url} (400, retry sem time_range também falhou: {e2})"
                ) from e2
        else:
            raise RuntimeError(f"falha HTTP em {url}: {e}") from e
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"falha HTTP em {url}: {e}") from e
    dt = time.time() - t0

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"resposta não é JSON válido: {e}") from e

    if status != 200:
        raise RuntimeError(f"HTTP {status} em {url}")

    # Log de status em stderr (1 linha) — não polui stdout quando --json
    print(
        f"status: HTTP {status} | t {dt:.2f}s | "
        f"{len(data.get('results', []))} resultados | engine-status: "
        f"{list((data.get('unresponsive_engines') or [])) or 'ok'}",
        file=sys.stderr,
    )

    # Truncar resultados ao limite pedido
    if limit and len(data.get("results", [])) > limit:
        data["results"] = data["results"][:limit]
    return data


def render_text(data: dict[str, Any], limit: int | None = None) -> str:
    """Formata saída humana (default quando --json não é passado)."""
    results = data.get("results", []) or []
    if not results:
        return f"⚠️  Nenhum resultado para: {data.get('query','')}"

    out: list[str] = []
    out.append(f"🔎  Busca: {data.get('query','')}  —  {len(results)} resultados")
    if data.get("answers"):
        for a in data["answers"][:2]:
            out.append(f"💡 Resposta direta: {a}")
    for i, r in enumerate(results[:limit] if limit else results, 1):
        title = r.get("title", "(sem título)")
        url = r.get("url", "")
        content = r.get("content", "").strip()
        engine = r.get("engine", "?")
        score = r.get("score")
        out.append(f"\n[{i}] {title}")
        out.append(f"    {url}")
        if content:
            # Truncar snippet pra ficar amigável no chat
            if len(content) > 240:
                content = content[:237].rstrip() + "…"
            out.append(f"    {content}")
        meta = f"engine={engine}"
        if score is not None:
            meta += f" | score={score:.2f}"
        out.append(f"    ({meta})")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Busca web via SearXNG (tools-searxng, 192.168.15.41:82)",
    )
    ap.add_argument("query", help="Termos de busca (aspas se tiver espaço)")
    ap.add_argument("-k", "--limit", type=int, default=10,
                    help="Número máximo de resultados (default 10)")
    ap.add_argument("--lang", default=None,
                    help="Filtro de idioma (ex.: pt-BR, en-US)")
    ap.add_argument("--time", choices=["d", "w", "m", "y"], default=None,
                    help="Janela temporal: d=1d, w=1sem, m=1mês, y=1ano")
    ap.add_argument("--engines", default=None,
                    help="Engines separados por vírgula (ex.: 'google,bing')")
    ap.add_argument("--safe", type=int, default=1, choices=[0, 1, 2],
                    help="Safesearch 0/1/2 (default 1)")
    ap.add_argument("--base-url", default=DEFAULT_URL,
                    help=f"Endpoint base (default {DEFAULT_URL})")
    ap.add_argument("--json", action="store_true",
                    help="Saída em JSON puro (pra piping/script)")
    args = ap.parse_args()

    try:
        data = search_json(
            args.query,
            limit=args.limit,
            lang=args.lang,
            time_range=args.time,
            engines=args.engines,
            safesearch=args.safe,
            base_url=args.base_url,
        )
    except (RuntimeError, ValueError) as e:
        print(f"❌  {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render_text(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
