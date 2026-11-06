#!/usr/bin/env python3
"""librarium-api.py — cliente REST do Librarium (física) para o Study-Agent.

O Librarium (LXC 192.168.15.201) é o catálogo de LIVROS FÍSICOS do William
(estante de casa). O MCP dele (http://192.168.15.201:8090/mcp) exige um token
de entrada `lbrm_mcp_*` que só existe no container — até o William fornecer,
esta REST API cobre 100% das consultas de leitura e a maioria das escritas.

Usage:
  librarium-api.py <comando> [args]

Comandos:
  stats                       contagens agregadas (livros, séries, autores, empréstimos)
  libraries                   bibliotecas visíveis
  members                     membros de uma biblioteca
  books [--library ID] [--q TEXTO] [--limit N] [--page N] [--status S]
  book <book_id>              registro completo de um livro
  search --query "..."        busca por título/autor (mesma rota de books com q)
  series [--query ...] [--library ID] [--incomplete]
  loans [--library ID] [--include-returned]
  shelves [--library ID]
  tags
  wishlist
  raw <path> [chave=valor]    GET arbitrário na API (ex.: raw me/counts)
  whoami                      usuário da credencial
  token-info                  metadados do PAT (nunca imprime o token)

Ler credenciais: data/perfil/bibliotecario/librarium-creds.json (gitignored).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("LIBRARIUM_API_URL", "http://192.168.15.201/api/v1")
CREDS = os.environ.get(
    "LIBRARIUM_CREDS",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "perfil",
        "bibliotecario",
        "librarium-creds.json",
    ),
)


def _creds() -> dict:
    path = CREDS
    if not os.path.exists(path):
        here = os.path.dirname(os.path.abspath(__file__))
        alt = os.path.join(os.path.dirname(here), "data", "perfil", "bibliotecario",
                           "librarium-creds.json")
        if os.path.exists(alt):
            path = alt
        else:
            sys.exit(f"[erro] credenciais nao encontradas em {path}")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _token() -> str:
    c = _creds()
    tok = c.get("pat") or c.get("access_token")
    if not tok:
        sys.exit("[erro] sem PAT em librarium-creds.json")
    return tok


def _req(method: str, path: str, body: dict | None = None) -> object:
    url = BASE + path if path.startswith("/") else f"{BASE}/{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_token()}")
    req.add_header("X-Librarium-Client", "iam")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        return {"_http_status": exc.code, "_error": raw}
    except Exception as exc:  # rede
        return {"_error": f"{type(exc).__name__}: {exc}"}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw}
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _dump(obj: object) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def _qs(**params) -> str:
    clean = {k: v for k, v in params.items() if v not in (None, "", False)}
    return ("?" + urllib.parse.urlencode(clean)) if clean else ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Cliente REST do Librarium (livros físicos)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("stats")
    sub.add_parser("libraries")
    sub.add_parser("tags")
    sub.add_parser("wishlist")
    sub.add_parser("whoami")
    sub.add_parser("token-info")

    p = sub.add_parser("members")
    p.add_argument("library_id")

    p = sub.add_parser("books")
    p.add_argument("--library", dest="library")
    p.add_argument("--q")
    p.add_argument("--author")
    p.add_argument("--tag")
    p.add_argument("--genre")
    p.add_argument("--status")
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--page", type=int, default=1)

    p = sub.add_parser("book")
    p.add_argument("book_id")

    p = sub.add_parser("search")
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=25)

    p = sub.add_parser("series")
    p.add_argument("--query")
    p.add_argument("--library", dest="library")
    p.add_argument("--incomplete", action="store_true")
    p.add_argument("--sort")
    p.add_argument("--limit", type=int, default=50)

    p = sub.add_parser("loans")
    p.add_argument("--library", dest="library", required=True)
    p.add_argument("--include-returned", action="store_true")

    p = sub.add_parser("shelves")
    p.add_argument("--library", dest="library")

    p = sub.add_parser("raw")
    p.add_argument("path")
    p.add_argument("params", nargs="*")

    args = ap.parse_args()
    c = args.cmd

    if c == "stats":
        _dump(_req("GET", "/me/counts"))
    elif c == "libraries":
        _dump(_req("GET", "/me/libraries"))
    elif c == "members":
        _dump(_req("GET", f"/libraries/{args.library_id}/members"))
    elif c == "books":
        _dump(_req("GET", "/me/books" + _qs(
            lib=args.library, q=args.q, author=args.author, tag=args.tag,
            genre=args.genre, status=args.status, limit=args.limit, page=args.page)))
    elif c == "book":
        _dump(_req("GET", f"/me/books/{args.book_id}"))
    elif c == "search":
        _dump(_req("GET", "/me/books" + _qs(q=args.query, limit=args.limit, page=1)))
    elif c == "series":
        _dump(_req("GET", "/me/series" + _qs(
            query=args.query, library_id=args.library,
            incomplete=args.incomplete or None, sort=args.sort, limit=args.limit)))
    elif c == "loans":
        _dump(_req("GET", "/me/loans" + _qs(
            library_id=args.library, include_returned=args.include_returned or None)))
    elif c == "shelves":
        _dump(_req("GET", "/me/shelves" + _qs(library_id=args.library)))
    elif c == "tags":
        _dump(_req("GET", "/me/tags"))
    elif c == "wishlist":
        _dump(_req("GET", "/me/wishlist"))
    elif c == "whoami":
        _dump(_req("GET", "/auth/me"))
    elif c == "token-info":
        creds = _creds()
        safe = {k: v for k, v in creds.items() if k not in ("pat", "access_token", "password")}
        if creds.get("pat"):
            safe["pat_prefix"] = creds["pat"][:9] + "..." + creds["pat"][-4:]
        safe["api_base"] = BASE
        _dump(safe)
    elif c == "raw":
        params = {}
        for kv in args.params:
            if "=" in kv:
                k, v = kv.split("=", 1)
                params[k] = v
        _dump(_req("GET", args.path + _qs(**params)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
