#!/usr/bin/env python3
"""biblio-api.py — cliente do biblio-mcp (fan-out: Anna's Archive + Libgen + Z-Library).

POR QUE ISTO EXISTE (pedido do William, 2026-11-05):
  "adicione esse no seu fluxo de aquisições: https://github.com/yashimosh/biblio-mcp"

O biblio-mcp e' um servidor MCP (Node/TypeScript) que faz fan-out de busca em
tres shadow libraries + Sci-Hub, com dedup por MD5 e rotacao de mirrors.
O `zlib-api.py` (eAPI do z-library) so' resolve o Z-LIBRARY e gasta COTA
(40 downloads/dia). O biblio-mcp abre o LIBGEN e o SCI-HUB, que NAO tem cota.

O QUE MUDA NA PRATICA:
  - Livros que o z-library nao devolve (ou que nao cabem na cota) passam a ter
    uma 2a via de aquisicao SEM GASTAR COTA.
  - Artigos cientificos (Sci-Hub, via DOI) entram no fluxo — antes impossivel.

COMO FUNCIONA (stdio JSON-RPC, sem HTTP):
  O biblio-mcp fala MCP por stdio. Este wrapper fala JSON-RPC 2.0 direto
  com o processo `node .tools/biblio-mcp/dist/index.js`, sem depender do
  suporte MCP do picoclaw (que exigiria reiniciar o gateway).

NUNCA imprime segredo. NUNCA baixa ebook para dentro de `data/` (o ebook
original vai para `data/biblioteca/_incoming/` e é apagado depois do upload
confirmado ao BookOrbit — mesma regra do `zlib-api.py`).

Uso:
  biblio-api.py mirrors
  biblio-api.py search "QUERY" [--limit N] [--source libgen|annas|zlibrary] [--lang portuguese]
  biblio-api.py papers "QUERY" [--limit N]
  biblio-api.py links MD5
  biblio-api.py details MD5
  biblio-api.py download MD5 [--dest DIR] [--ext epub]
  biblio-api.py doctor
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIBLIO_DIR = ROOT / ".tools" / "biblio-mcp"
BIBLIO_JS = BIBLIO_DIR / "dist" / "index.js"
DOWNLOAD_DIR = ROOT / "data" / "biblioteca" / "_incoming"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# Mirrors que MEDI respondedem desta rede (2026-11-05):
#   libgen.li/index.php  -> busca real (107 KB com md5 + ids)
#   sci-hub.ren/<doi>    -> resolve PDF por DOI
# Os defaults do biblio-mcp (annas-archive.org, libgen.li, sci-hub.se) NAO
# funcionam desta rede — por isso os overrides abaixo.
#
# BUG (2026-11-05, 1a tentativa): os mirrors foram passados SEM o scheme
# ("libgen.li"). O biblio-mcp monta a URL como "<mirror>/search.php" e o
# fetch() do Node falha com "Failed to parse URL from libgen.li/search.php" —
# as 3 fontes davam erro e a busca voltava VAZIA. O scheme e' obrigatorio.
MIRRORS_ENV = {
    "BIBLIO_ANNAS_MIRRORS": "https://annas-archive.li,https://annas-archive.gs,https://annas-archive.org",
    "BIBLIO_LIBGEN_MIRRORS": "https://libgen.li,https://libgen.onl,https://libgen.vg",
    "BIBLIO_SCIHUB_MIRRORS": "https://sci-hub.ren,https://sci-hub.ru,https://sci-hub.st",
    "BIBLIO_ZLIB_MIRRORS": "https://z-lib.gd,https://z-lib.sk",
    "BIBLIO_TIMEOUT_MS": "30000",
}


class Biblio:
    """Cliente MCP por stdio (JSON-RPC 2.0 linha a linha)."""

    def __init__(self, timeout=45):
        if not BIBLIO_JS.exists():
            raise RuntimeError(
                "biblio-mcp nao buildado. Rode:\n"
                "  cd %s && npm install && npm run build" % BIBLIO_DIR
            )
        env = dict(os.environ)
        env.update(MIRRORS_ENV)
        self.proc = subprocess.Popen(
            ["node", str(BIBLIO_JS)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, text=True, bufsize=1,
        )
        self._id = 0
        self.timeout = timeout
        self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "biblio-api", "version": "1.0"},
        })
        self._notify("notifications/initialized", {})

    def _notify(self, method, params):
        try:
            self.proc.stdin.write(json.dumps(
                {"jsonrpc": "2.0", "method": method, "params": params}) + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, ValueError):
            pass

    def _rpc(self, method, params, timeout=None):
        self._id += 1
        rid = self._id
        msg = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        deadline = time.time() + (timeout or self.timeout)
        while time.time() < deadline:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("biblio-mcp encerrou a conexao (erro: %s)"
                                   % self._stderr_tail())
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except ValueError:
                continue
            if data.get("id") != rid:
                continue
            if "error" in data:
                raise RuntimeError("biblio-mcp erro em %s: %s"
                                   % (method, data["error"]))
            return data.get("result") or {}
        raise RuntimeError("timeout (%ss) esperando %s" % (timeout or self.timeout, method))

    def _stderr_tail(self):
        try:
            self.proc.stderr.flush()
        except Exception:
            pass
        return "(sem detalhe)"

    def call(self, tool, args, timeout=None):
        res = self._rpc("tools/call", {"name": tool, "arguments": args}, timeout=timeout)
        # MCP devolve content[] com type=text e JSON dentro
        chunks = (res.get("content") or [])
        texts = [c.get("text", "") for c in chunks if c.get("type") == "text"]
        blob = "\n".join(texts).strip()
        if not blob:
            return {}
        try:
            return json.loads(blob)
        except ValueError:
            return {"_raw": blob}

    def close(self):
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass


# --------------------------------------------------------------------------
# comandos
# --------------------------------------------------------------------------
def cmd_doctor(a):
    """Verifica: build presente, node ok, e as 4 fontes respondem."""
    out = {"node": None, "build": BIBLIO_JS.exists(), "fontes": {}}
    try:
        r = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
        out["node"] = r.stdout.strip()
    except Exception as e:
        out["node"] = "ERRO: %s" % e

    probes = {
        "libgen": "https://libgen.li/index.php?req=test",
        "scihub": "https://sci-hub.ren/",
        "annas": "https://annas-archive.li/search?q=test",
        "zlib": "https://z-lib.gd/",
    }
    for nome, url in probes.items():
        try:
            r = subprocess.run(
                ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "12",
                 "-H", "User-Agent: %s" % UA, url],
                capture_output=True, text=True, timeout=25)
            out["fontes"][nome] = r.stdout.strip() or "sem resposta"
        except Exception as e:
            out["fontes"][nome] = "ERRO: %s" % e

    try:
        b = Biblio()
        out["mcp"] = "OK — initialize + tools/list"
        b.close()
    except Exception as e:
        out["mcp"] = "ERRO: %s" % e
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def cmd_mirrors(a):
    for k, v in MIRRORS_ENV.items():
        print("  %s=%s" % (k, v))
    return 0


def cmd_search(a):
    args = {"query": a.query, "limit": a.limit}
    if a.source:
        args["sources"] = [a.source]
    b = Biblio()
    try:
        d = b.call("search_books", args)
    finally:
        b.close()
    res = d.get("results") or []
    out = []
    for r in res:
        out.append({
            "source": r.get("source"), "md5": r.get("md5"),
            "title": r.get("title"), "author": r.get("author"),
            "year": r.get("year"), "language": r.get("language"),
            "format": r.get("format"), "size": r.get("size"),
            "publisher": r.get("publisher"),
        })
    if a.lang:
        alvo = a.lang.lower()
        out = [o for o in out
               if (o.get("language") or "").lower().startswith(alvo)]
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def cmd_papers(a):
    b = Biblio()
    try:
        d = b.call("search_papers", {"query": a.query, "limit": a.limit})
    finally:
        b.close()
    print(json.dumps(d.get("results") or [], ensure_ascii=False, indent=1))
    return 0


def cmd_paper(a):
    """Resolve o PDF de um artigo por DOI (Sci-Hub) e mostra o link direto."""
    b = Biblio()
    try:
        d = b.call("get_paper", {"identifier": a.doi})
    finally:
        b.close()
    if a.download:
        url = d.get("pdfUrl") or ""
        if not url:
            print(json.dumps({"ok": False, "erro": "sem pdfUrl", "doi": a.doi},
                             ensure_ascii=False))
            return 2
        dest = Path(a.dest) if a.dest else DOWNLOAD_DIR
        dest.mkdir(parents=True, exist_ok=True)
        nome = re.sub(r"[^0-9A-Za-z._-]+", "_", a.doi)[:100]
        out = dest / (nome + ".pdf")
        subprocess.run(
            ["curl", "-sSL", "--max-time", "180", "-H", "User-Agent: %s" % UA,
             "-o", str(out), url],
            capture_output=True, text=True)
        if out.exists() and out.stat().st_size > 5000:
            print(json.dumps({"ok": True, "path": str(out),
                              "bytes": out.stat().st_size,
                              "doi": a.doi}, ensure_ascii=False))
            return 0
        if out.exists():
            out.unlink()
        print(json.dumps({"ok": False, "erro": "download do PDF falhou",
                          "doi": a.doi}, ensure_ascii=False))
        return 2
    print(json.dumps(d, ensure_ascii=False, indent=1))
    return 0


def cmd_links(a):
    b = Biblio()
    try:
        d = b.call("get_download_links", {"md5": a.md5})
    finally:
        b.close()
    print(json.dumps(d, ensure_ascii=False, indent=1))
    return 0


def cmd_details(a):
    b = Biblio()
    try:
        d = b.call("book_details", {"md5": a.md5})
    finally:
        b.close()
    print(json.dumps(d, ensure_ascii=False, indent=1))
    return 0


def _safe_name(s):
    s = re.sub(r"[^\w\s.-]", "", s or "")
    s = re.sub(r"[\s_]+", "-", s).strip("-.")
    return s[:110] or "livro"


def cmd_download(a):
    """Baixa via MCP (download_book) OU via link direto do Libgen (fallback)."""
    dest = Path(a.dest) if a.dest else DOWNLOAD_DIR
    dest.mkdir(parents=True, exist_ok=True)

    b = Biblio(timeout=90)
    try:
        d = b.call("download_book", {"md5": a.md5, "output_dir": str(dest)}, timeout=240)
    except Exception as e:
        d = {"_erro": str(e)}
    finally:
        b.close()

    # o MCP pode devolver caminho absoluto ou relativo
    achados = []
    for k in ("path", "file", "output_path", "outputPath"):
        v = d.get(k)
        if isinstance(v, str) and v:
            achados.append(v)
    if isinstance(d.get("files"), list):
        for f in d["files"]:
            if isinstance(f, str):
                achados.append(f)
            elif isinstance(f, dict) and f.get("path"):
                achados.append(f["path"])

    for cand in achados:
        p = Path(cand)
        if not p.is_absolute():
            p = dest / p
        if p.exists() and p.stat().st_size > 2000:
            final = dest / (_safe_name(p.stem) + p.suffix)
            if final != p:
                p.rename(final)
            print(json.dumps({"ok": True, "path": str(final),
                              "bytes": final.stat().st_size,
                              "ext": final.suffix.lstrip(".")},
                             ensure_ascii=False))
            return 0

    # FALLBACK: link direto (Libgen get.php) + curl
    try:
        b2 = Biblio()
        try:
            links = b2.call("get_download_links", {"md5": a.md5}).get("links") or []
        finally:
            b2.close()
    except Exception as e:
        links = []
        print("aviso: get_download_links falhou (%s)" % e, file=sys.stderr)

    diretos = [l for l in links if l.get("direct") and l.get("url")]
    for l in diretos:
        url = l["url"]
        ext = a.ext or "epub"
        out = dest / ("biblio-%s.%s" % (a.md5[:12], ext))
        r = subprocess.run(
            ["curl", "-sSL", "--max-time", "280", "-H", "User-Agent: %s" % UA,
             "-o", str(out), url],
            capture_output=True, text=True)
        if out.exists() and out.stat().st_size > 2000:
            print(json.dumps({"ok": True, "path": str(out),
                              "bytes": out.stat().st_size, "ext": ext,
                              "via": "link-direto"}, ensure_ascii=False))
            return 0
        if out.exists():
            out.unlink()

    print(json.dumps({"ok": False, "erro": "nenhum link direto baixou",
                      "md5": a.md5,
                      "links": len(links)}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Cliente do biblio-mcp (stdio MCP)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("doctor"); p.set_defaults(func=cmd_doctor)
    p = sub.add_parser("mirrors"); p.set_defaults(func=cmd_mirrors)

    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--source", choices=["libgen", "annas", "zlibrary"])
    p.add_argument("--lang")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("papers")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_papers)

    p = sub.add_parser("paper")
    p.add_argument("doi")
    p.add_argument("--download", action="store_true", help="baixa o PDF")
    p.add_argument("--dest")
    p.set_defaults(func=cmd_paper)

    p = sub.add_parser("links"); p.add_argument("md5"); p.set_defaults(func=cmd_links)
    p = sub.add_parser("details"); p.add_argument("md5"); p.set_defaults(func=cmd_details)

    p = sub.add_parser("download")
    p.add_argument("md5")
    p.add_argument("--dest")
    p.add_argument("--ext")
    p.set_defaults(func=cmd_download)

    args = ap.parse_args()
    try:
        sys.exit(args.func(args))
    except RuntimeError as e:
        print(json.dumps({"ok": False, "erro": str(e)}, ensure_ascii=False))
        sys.exit(2)
