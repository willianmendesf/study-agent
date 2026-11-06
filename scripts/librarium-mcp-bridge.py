#!/usr/bin/env python3
"""librarium-mcp-bridge.py — servidor MCP (stdio) para o Librarium do William.

POR QUE EXISTE (2026-11-06)
---------------------------
O `librarium-mcp` oficial (http://192.168.15.201:8090/mcp) exige um token de
ENTRADA (`lbrm_mcp_*`) que vive dentro do container — inacessível daqui.
Mas ele é, nas palavras do próprio autor, "just another Librarium API client".

Este bridge faz o mesmo pela via que funciona: fala a **API REST** do
Librarium (http://192.168.15.201/api/v1) com o PAT `lbrm_pat_*` do IAM e
expõe os mesmos tools ao picoclaw, via stdio.

Credenciais: data/perfil/bibliotecario/librarium-creds.json (gitignored).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from mcp.server.mcpserver import MCPServer

BASE = os.environ.get("LIBRARIUM_API_URL", "http://192.168.15.201/api/v1")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDS = os.environ.get(
    "LIBRARIUM_CREDS",
    os.path.join(ROOT, "data", "perfil", "bibliotecario", "librarium-creds.json"),
)

mcp = MCPServer("librarium")


def _token() -> str:
    with open(CREDS, encoding="utf-8") as fh:
        c = json.load(fh)
    tok = c.get("pat") or c.get("access_token")
    if not tok:
        raise RuntimeError(f"sem PAT em {CREDS}")
    return tok


def _api(method: str, path: str, body: dict | None = None) -> object:
    url = BASE + (path if path.startswith("/") else f"/{path}")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_token()}")
    req.add_header("X-Librarium-Client", "mcp")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        body_txt = exc.read().decode("utf-8", "replace")[:400]
        return {"_http_status": exc.code, "_error": body_txt}
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw[:2000]}
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _qs(**params) -> str:
    clean = {k: v for k, v in params.items() if v not in (None, "", False)}
    return ("?" + urllib.parse.urlencode(clean)) if clean else ""


def _fmt(obj: object) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def _media_types() -> list[str]:
    data = _api("GET", "/media-types")
    if isinstance(data, list):
        return [m.get("name", "") for m in data if isinstance(m, dict)]
    return []


def _media_type_id(name: str) -> str | None:
    data = _api("GET", "/media-types")
    if isinstance(data, list):
        for m in data:
            if isinstance(m, dict) and m.get("name") == name:
                return m.get("id")
    return None


# ── leitura ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_libraries() -> str:
    """Bibliotecas (estantes) que o usuário pode acessar: id, nome, descrição."""
    return _fmt(_api("GET", "/me/libraries"))


@mcp.tool()
def search_books(
    query: str | None = None,
    author: str | None = None,
    tag: str | None = None,
    genre: str | None = None,
    read_status: str | None = None,
    library_id: str | None = None,
    limit: int = 25,
    page: int = 1,
) -> str:
    """Busca livros na coleção. Filtros: título/autor (query), autor, tag,
    gênero, status de leitura (unread|reading|read|did_not_finish), biblioteca."""
    return _fmt(_api("GET", "/me/books" + _qs(
        q=query, author=author, tag=tag, genre=genre, status=read_status,
        lib=library_id, limit=limit, page=page)))


@mcp.tool()
def get_book(book_id: str) -> str:
    """Registro completo de um livro: contribuidores, tags, gêneros, séries,
    bibliotecas e status de leitura do usuário."""
    return _fmt(_api("GET", f"/books/{book_id}"))


@mcp.tool()
def list_series(
    query: str | None = None,
    library_id: str | None = None,
    genre: str | None = None,
    incomplete: bool = False,
    sort: str | None = None,
    limit: int = 50,
) -> str:
    """Séries da coleção com quantos volumes estão na estante e quantos faltam.
    `incomplete=true` esconde as séries completas."""
    return _fmt(_api("GET", "/me/series" + _qs(
        query=query, library_id=library_id, genre=genre,
        incomplete=incomplete or None, sort=sort, limit=limit)))


@mcp.tool()
def list_loans(library_id: str, include_returned: bool = False) -> str:
    """Empréstimos da biblioteca. Por padrão só os ativos."""
    return _fmt(_api("GET", "/me/loans" + _qs(
        library_id=library_id, include_returned=include_returned or None)))


@mcp.tool()
def list_shelves(library_id: str | None = None) -> str:
    """Prateleiras (shelves) do usuário."""
    return _fmt(_api("GET", "/me/shelves" + _qs(library_id=library_id)))


@mcp.tool()
def list_tags() -> str:
    """Etiquetas (tags) do usuário."""
    return _fmt(_api("GET", "/me/tags"))


@mcp.tool()
def collection_stats() -> str:
    """Contagens agregadas: livros, séries, autores, empréstimos, sugestões."""
    return _fmt(_api("GET", "/me/counts"))


# ── escrita ──────────────────────────────────────────────────────────────────

@mcp.tool()
def add_book_by_isbn(
    isbn: str,
    library_id: str,
    title: str,
    media_type: str = "novel",
    book_format: str | None = None,
) -> str:
    """Cataloga um livro na biblioteca informada.
    isbn: ISBN-10 ou ISBN-13 (13 dígitos, sem hífens).
    title: título — OBRIGATÓRIO na API (a API não resolve o título sozinha).
    media_type: novel | non_fiction | textbook | manga | comic | graphic_novel |
    short_story_collection | poetry | artbook | magazine | anthology | ...
    book_format: paperback | hardcover | ebook | audiobook | comic | box_set.
    A metadata/capa entram de forma assíncrona."""
    mt_id = _media_type_id(media_type)
    if not mt_id:
        return _fmt({"_error": f"media_type desconhecido: {media_type}",
                     "_disponiveis": _media_types()})
    payload: dict = {"title": title, "media_type_id": mt_id}
    if isbn:
        payload["isbn"] = isbn
    if book_format:
        payload["format"] = book_format
    return _fmt(_api("POST", f"/libraries/{library_id}/books", payload))


@mcp.tool()
def set_read_status(book_id: str, status: str) -> str:
    """Marca o estado de leitura: unread | reading | read | did_not_finish.
    O estado pertence à OBRA, não ao exemplar — marcar lido marca em todos."""
    return _fmt(_api("PUT", f"/books/{book_id}/me", {"read_status": status}))


@mcp.tool()
def set_rating(book_id: str, rating: int | None) -> str:
    """Nota do usuário: 1-10 (meia estrela, ou seja 1,5 = 3). None limpa."""
    return _fmt(_api("PUT", f"/books/{book_id}/me", {"rating": rating}))


@mcp.tool()
def mark_favorite(book_id: str, is_favorite: bool = True) -> str:
    """Marca (ou desmarca) o livro como favorito do usuário."""
    return _fmt(_api("PUT", f"/books/{book_id}/me", {"is_favorite": is_favorite}))


@mcp.tool()
def remove_book(library_id: str, book_id: str) -> str:
    """Remove um livro da biblioteca (apaga o registro de catálogo)."""
    return _fmt(_api("DELETE", f"/libraries/{library_id}/books/{book_id}"))


@mcp.tool()
def write_review(
    book_id: str,
    notes: str | None = None,
    review: str | None = None,
    is_favorite: bool | None = None,
) -> str:
    """Anotações (privadas) e avaliação (visível aos membros) de um livro."""
    payload = {k: v for k, v in (
        ("notes", notes), ("review", review), ("is_favorite", is_favorite)
    ) if v is not None}
    return _fmt(_api("PUT", f"/books/{book_id}/me", payload))


if __name__ == "__main__":
    mcp.run()
