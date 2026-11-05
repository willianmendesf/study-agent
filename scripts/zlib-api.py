#!/usr/bin/env python3
"""Cliente eAPI do Z-Library para o picoclaw (sem node/npx).

Uso:
  zlib-api.py domains
  zlib-api.py limits [conta]
  zlib-api.py search "QUERY" [conta] [--limit N] [--lang portuguese]
  zlib-api.py download BOOK_ID HASH [conta] [--ext pdf] [--dest DIR]
  zlib-api.py formats BOOK_ID HASH [conta]

Contas e credenciais vem de data/perfil/bibliotecario/zlib-credentials.yaml
(ou do cache ~/.zlib-mcp/.account-env-cache.json). NUNCA imprime segredo.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREDS_YAML = ROOT / "data" / "perfil" / "bibliotecario" / "zlib-credentials.yaml"
CACHE = Path.home() / ".zlib-mcp" / ".account-env-cache.json"
DOWNLOAD_DIR = ROOT / "data" / "biblioteca" / "_incoming"

DOMAINS = [
    "https://z-lib.gd",
    "https://z-lib.sk",
    "https://z-lib.es",
    "https://z-lib.rs",
    "https://z-lib.fm",
    "https://z-lib.se",
    "https://z-lib.la",
    "https://z-lib.li",
    "https://z-lib.cz",
    "https://z-lib.su",
    "https://z-lib.org",
    "https://z-lib.net",
    "https://z-lib.io",
]

UA = "Mozilla/5.0 (Android 12; Mobile)"
ORDER = ["zlib", "zlib2", "zlib3", "zlib4"]


# --------------------------------------------------------------------------
# credenciais
# --------------------------------------------------------------------------
def load_accounts():
    envs = {}
    if CACHE.exists():
        try:
            envs = json.load(open(CACHE))
        except Exception:
            envs = {}
    if not envs:
        try:
            txt = CREDS_YAML.read_text(encoding="utf-8")
        except Exception:
            return {}
        blocks = txt.split("- alias:")
        for i, b in enumerate(blocks[1:]):
            rid = re.search(r"remix_id:\s*'?([0-9]+)'?", b)
            rkey = re.search(r"remix_key:\s*'?([A-Za-z0-9]+)'?", b)
            if rid and rkey and i < len(ORDER):
                envs[ORDER[i]] = {"ZLIB_REMIX_ID": rid.group(1),
                                  "ZLIB_REMIX_KEY": rkey.group(1)}
    return envs


def cookies_for(account):
    envs = load_accounts()
    if account not in envs:
        raise SystemExit(f"ERRO: sem credenciais para a conta '{account}' "
                         f"(disponiveis: {', '.join(envs) or 'nenhuma'})")
    e = envs[account]
    return f"remix_userid={e['ZLIB_REMIX_ID']}; remix_userkey={e['ZLIB_REMIX_KEY']}"


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def _curl(args, timeout=40):
    import subprocess
    try:
        r = subprocess.run(["curl", "-sS", "--max-time", str(timeout)] + args,
                           capture_output=True, text=True, timeout=timeout + 15)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    return r.stdout


def _domain():
    """Descobre um dominio VIVO (cache em /tmp).

    BUG 2026-11-05: a descoberta antiga aceitava qualquer resposta HTTP
    (200/400/401/403), mas o `z-lib.sk` responde 307 (DiamWall) em
    /eapi/book/search — o `search` entrava em loop de redirect e a busca
    nunca funcionava. Agora o criterio e' o SEARCH REAL: so vale o dominio
    que devolve `success:1` numa busca de teste.
    """
    cache = Path("/tmp/.zlib-domain")
    if cache.exists():
        d = cache.read_text().strip()
        if d and _search_ok(d, "Dumbo"):
            return d
        try:
            cache.unlink()
        except Exception:
            pass
    for d in DOMAINS:
        if _search_ok(d, "Dumbo"):
            cache.write_text(d)
            return d
    return DOMAINS[0]


def _search_ok(dominio, query="Dumbo"):
    """True se o dominio responde um search REAL (success:1) em <5s."""
    import subprocess
    args = ["-sS", "--max-time", "12", "-X", "POST",
            f"{dominio}/eapi/book/search",
            "-H", f"User-Agent: {UA}",
            "--data-urlencode", f"message={query}",
            "--data-urlencode", "limit=1"]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=25)
        return '"success":1' in r.stdout
    except Exception:
        return False


def api_post(path, data, account, timeout=45):
    d = _domain()
    args = ["-L", "-X", "POST", f"{d}{path}", "-H", f"User-Agent: {UA}",
            "-b", cookies_for(account)]
    for k, v in data.items():
        args += ["--data-urlencode", f"{k}={v}"]
    out = _curl(args, timeout=timeout)
    return _parse(out)


def api_get(path, account, timeout=45):
    d = _domain()
    out = _curl([f"{d}{path}", "-H", f"User-Agent: {UA}", "-b", cookies_for(account)],
                timeout=timeout)
    return _parse(out)


def _parse(out):
    if out is None:
        return {"success": 0, "error": "sem resposta (rede/timeout)"}
    out = out.strip()
    if not out:
        return {"success": 0, "error": "resposta vazia"}
    try:
        return json.loads(out)
    except Exception:
        i = out.find("{")
        if i >= 0:
            try:
                return json.loads(out[i:])
            except Exception:
                pass
        return {"success": 0, "error": out[:200]}


# --------------------------------------------------------------------------
# comandos
# --------------------------------------------------------------------------
def cmd_domains(a):
    for d in DOMAINS:
        code = _curl(["-o", "/dev/null", "-w", "%{http_code}", "-X", "POST",
                      f"{d}/eapi/user/login", "-H", f"User-Agent: {UA}"], timeout=20)
        print(f"  {d}: {code or 'sem resposta'}")
    print("ativo:", _domain())


def cmd_limits(a):
    accs = [a.conta] if a.conta else list(load_accounts().keys())
    for acc in accs:
        d = api_get("/eapi/user/profile", acc)
        u = d.get("user") or {}
        lim = u.get("downloads_limit") or 0
        hoje = u.get("downloads_today") or 0
        # BUG (2026-11-05): imprimia `remaining=downloads_limit` — o LIMITE, nao
        # o que sobra. Dizia "remaining=10" com a cota ja esgotada (10/10),
        # e a rotina acreditava que ainda tinha 30 downloads e queimava
        # tempo procurando o que nao dava. O que sobra e' limite - hoje.
        print(f"  {acc}: today={hoje} limit={lim} "
              f"remaining={max(0, lim - hoje)} "
              f"err={d.get('error', '')}")


def cmd_search(a):
    data = {"message": a.query, "limit": str(a.limit)}
    if a.lang:
        data["languages[]"] = a.lang
    if a.ext:
        data["extensions[]"] = a.ext
    d = api_post("/eapi/book/search", data, a.conta)
    if not d.get("success"):
        print(json.dumps(d, ensure_ascii=False)[:400])
        return 2
    books = d.get("books") or []
    if not books:
        print("[]")
        return 0
    out = []
    for b in books:
        out.append({
            "id": b.get("id"), "hash": b.get("hash"),
            "title": b.get("title"), "author": b.get("author"),
            "extension": b.get("extension"), "lang": b.get("language"),
            "year": b.get("year"), "size": b.get("filesizeString") or b.get("filesize"),
            "publisher": b.get("publisher"),
        })
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def cmd_formats(a):
    d = api_get(f"/eapi/book/{a.book_id}/{a.hash}/formats", a.conta)
    if not d.get("success"):
        print(json.dumps(d, ensure_ascii=False)[:400])
        return 2
    out = []
    for b in d.get("books") or []:
        out.append({"id": b.get("id"), "hash": b.get("hash"),
                    "ext": b.get("extension"), "size": b.get("filesizeString"),
                    "lang": b.get("language")})
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def _safe_name(s):
    s = re.sub(r"[^\w\s.-]", "", s or "")
    s = re.sub(r"[\s_]+", "-", s).strip("-.")
    return s[:120] or "livro"


def cmd_download(a):
    d = api_get(f"/eapi/book/{a.book_id}/{a.hash}/file", a.conta)
    if not d.get("success"):
        print(json.dumps(d, ensure_ascii=False)[:400])
        return 2
    f = d.get("file") or {}
    link = f.get("downloadLink")
    ext = (f.get("extension") or a.ext or "epub").lower()
    if not link:
        print(json.dumps(d, ensure_ascii=False)[:400])
        return 2
    dest = Path(a.dest) if a.dest else DOWNLOAD_DIR
    dest.mkdir(parents=True, exist_ok=True)
    name = _safe_name(f.get("name") or f"zlib-{a.book_id}")
    out = dest / f"{name}.{ext}"
    r = _curl(["-L", "-o", str(out), "-H", f"User-Agent: {UA}", link], timeout=280)
    if out.exists() and out.stat().st_size > 2000:
        print(json.dumps({"ok": True, "path": str(out),
                          "bytes": out.stat().st_size, "ext": ext}, ensure_ascii=False))
        return 0
    print(json.dumps({"ok": False, "erro": "download vazio/falhou",
                      "path": str(out) if out.exists() else None}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("domains"); p.set_defaults(func=cmd_domains)

    p = sub.add_parser("limits")
    p.add_argument("conta", nargs="?")
    p.set_defaults(func=cmd_limits)

    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("conta", nargs="?", default="zlib2")
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--lang", default=None)
    p.add_argument("--ext", default=None)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("formats")
    p.add_argument("book_id")
    p.add_argument("hash")
    p.add_argument("conta", nargs="?", default="zlib2")
    p.set_defaults(func=cmd_formats)

    p = sub.add_parser("download")
    p.add_argument("book_id")
    p.add_argument("hash")
    p.add_argument("conta", nargs="?", default="zlib2")
    p.add_argument("--dest", default=None)
    p.add_argument("--ext", default=None)
    p.set_defaults(func=cmd_download)

    a = ap.parse_args()
    sys.exit(a.func(a))
