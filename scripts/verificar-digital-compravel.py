#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar-digital-compravel.py — antes de ESCANEAR, provar que NAO existe
DIGITAL COMPRAVEL (z-library / loja / ebook).

Pedido literal do William (2026-11-07):
  "antes de propor eu escanear, deveria ter buscado se tem pra comprar dele
   digital/ebook, escanear e se nao tiver como comprar digital/ebook."

REGRA (ordem, e a ordem e o que importa):
  VIA 1  digital JÁ NO ACERVO          -> usar (nao comprar, nao escanear)
  VIA 2  digital COMPRAVEL existe      -> COMPRAR digital (preferir ebook)
  VIA 3  SEM digital compravel, tem FISICO -> ESCANEAR o exemplar
  VIA 4  nem digital nem fisico        -> comprar/baixar

Este script faz a ETAPA "digital compravel existe?" para a fila de fisicos,
usando BUSCA REAL (z-library eAPI + SearXNG). Nada e inventado: se a busca
falhou (rede/engine), o item fica como "indeterminado" e NAO e marcado como
"sem digital" — para nao empurrar erro de busca para escanear.

Saida (incremental, retomada): data/perfil/bibliotecario/digital-compravel.jsonl
"""
import json
import re
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PERFIL = ROOT / "data/perfil/bibliotecario"
TRIAGEM = PERFIL / "triagem-aquisicao.yaml"
SAIDA = PERFIL / "digital-compravel.jsonl"
SEARXNG = "http://192.168.15.41:82/search"
ZLIB = ROOT / "scripts/zlib-api.py"

# Engines que devolvem pagina de PRODUTO (medido 2026-11-07).
ENGINES = "yahoo,bing,yandex,360search"

LOJAS = {
    "amazon.com.br": "Amazon.com.br",
    "mercadolivre.com.br": "Mercado Livre",
    "shopee.com.br": "Shopee",
    "saraiva.com.br": "Saraiva",
    "cultura.com.br": "Cultura",
    "estantica.com.br": "Estantica",
    "estantevirtual.com.br": "Estante Virtual",
    "bookshop.com.br": "Bookshop",
    "ler.com.br": "Livraria Cultura",
}

PARADA = {"de", "da", "do", "das", "dos", "a", "o", "e", "em", "para", "com",
          "the", "of", "and"}

_lock = threading.Lock()


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", s.lower())


def tokens(s):
    return set(t for t in norm(s).split() if t and t not in PARADA)


def _hoje():
    import datetime
    return datetime.date.today().isoformat()


def _agora():
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


# ------------------------------------------------------------------ z-library

def zlib_buscar(titulo, autor, contas=("zlib2", "zlib3", "zlib4"), limite=20):
    """Busca REAL no z-library. Devolve (lista, ok_de_busca).

    ok_de_busca=False significa "a busca nao rodou" (rede/erro) — nesse caso
    o item NAO pode ser marcado como 'sem digital'.
    """
    queries = [titulo]
    if autor:
        queries.append(f"{titulo} {autor}")
    for c in contas:
        for q in queries:
            try:
                p = subprocess.run(
                    [sys.executable, str(ZLIB), "search", q, c, "--limit", str(limite)],
                    capture_output=True, text=True, timeout=100)
            except Exception:
                continue
            txt = (p.stdout or "").strip()
            if not txt:
                continue
            try:
                data = json.loads(txt)
            except Exception:
                continue
            itens = data if isinstance(data, list) else (data.get("results") or [])
            return itens, True
    return [], False


def zlib_casa(itens, titulo, autor):
    """Filtra os resultados do z-library pelo titulo/autor (casamento estrito)."""
    t_tok = tokens(titulo)
    a_tok = tokens(autor) if autor else set()
    achados = []
    for it in itens:
        tt = tokens((it.get("title") or "") + " " + (it.get("author") or ""))
        cov_t = len(t_tok & tt) / max(1, len(t_tok))
        if cov_t < 0.6:
            continue
        if a_tok:
            cov_a = len(a_tok & tt) / max(1, len(a_tok))
            if cov_a == 0.0:
                continue
        else:
            cov_a = 0.0
        achados.append({
            "id": it.get("id"),
            "hash": it.get("hash"),
            "title": it.get("title"),
            "author": it.get("author"),
            "extension": it.get("extension"),
            "lang": it.get("lang"),
            "year": it.get("year"),
            "size": it.get("size"),
            "publisher": it.get("publisher"),
            "score": round(0.72 * cov_t + 0.28 * cov_a, 3),
        })
    achados.sort(key=lambda x: -x["score"])
    return achados


# ------------------------------------------------------------------ lojas

def searxng(query, engines=ENGINES, timeout=25):
    params = urllib.parse.urlencode({"format": "json", "q": query,
                                     "language": "pt-BR", "safesearch": 0,
                                     "engines": engines})
    try:
        with urllib.request.urlopen(f"{SEARXNG}?{params}", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"results": [], "erro": str(e)}


def classificar(url):
    for dom, nome in LOJAS.items():
        if dom in url:
            return dom, nome
    return None, None


def eh_digital(url, texto):
    """O anuncio e um ebook/Kindle ou um livro impresso?"""
    u = url.lower()
    t = texto.lower()
    if "-ebook" in u or "/kindle" in u or "ebook" in t or "kindle" in t \
       or "e-book" in t or "epub" in t or "pdf" in t:
        return True
    return False


def lojas_buscar(titulo, autor):
    t_tok = tokens(titulo)
    a_tok = tokens(autor) if autor else set()
    consultas = [
        f'"{titulo}" {autor or ""} comprar livro'.strip(),
        f'"{titulo}" {autor or ""} ebook comprar'.strip(),
        f'{titulo} {autor or ""} comprar exemplar'.strip(),
    ]
    achados = {}
    busca_ok = False
    for q in consultas:
        d = searxng(q)
        res = d.get("results") or []
        if res:
            busca_ok = True
        for r in res:
            url = r.get("url") or ""
            dom, nome = classificar(url)
            if not dom:
                continue
            texto = (r.get("title") or "") + " " + (r.get("content") or "")
            tt = tokens(texto)
            cov_t = len(t_tok & tt) / max(1, len(t_tok))
            if cov_t < 0.6:
                continue
            if a_tok:
                cov_a = len(a_tok & tt) / max(1, len(a_tok))
                if cov_a == 0.0:
                    continue
            else:
                cov_a = 0.0
            score = round(0.72 * cov_t + 0.28 * cov_a, 3)
            chave = (dom, url)
            reg = achados.get(chave)
            if reg is None or score > reg["score"]:
                achados[chave] = {
                    "loja": dom,
                    "loja_nome": nome,
                    "url": url,
                    "titulo_anuncio": (r.get("title") or "").strip()[:200],
                    "snippet": re.sub(r"\s+", " ", (r.get("content") or ""))[:220],
                    "score_aderencia": score,
                    "digital": eh_digital(url, texto),
                }
        if achados:
            break
        time.sleep(1.2)
    return list(achados.values()), busca_ok


# ------------------------------------------------------------------ worker

def processar(item):
    titulo = item["titulo"]
    autor = item.get("autor") or ""
    reg = {
        "data": _hoje(),
        "hora": _agora(),
        "titulo": titulo,
        "autor": autor or None,
        "slug": item.get("slug"),
        "origem": item.get("origem"),
        "onde": item.get("onde"),
    }

    z_itens, z_ok = zlib_buscar(titulo, autor)
    z_casados = zlib_casa(z_itens, titulo, autor) if z_ok else []
    reg["zlib"] = {"busca_ok": z_ok, "candidatos": z_casados[:5],
                   "bruto": len(z_itens)}

    l_itens, l_ok = lojas_buscar(titulo, autor)
    reg["lojas"] = l_itens
    reg["lojas_busca_ok"] = l_ok

    dig_zlib = [c for c in z_casados if (c.get("extension") or "").lower() in
                ("epub", "mobi", "azw3", "pdf", "fb2", "djvu", "txt")]
    dig_loja = [l for l in l_itens if l.get("digital")]
    imp_loja = [l for l in l_itens if not l.get("digital")]

    if dig_zlib or dig_loja:
        reg["veredito"] = "existe_digital_compravel"
        reg["vias"] = []
        if dig_zlib:
            reg["vias"].append("z-library (ebook)")
        if dig_loja:
            reg["vias"].append("loja (ebook)")
    elif z_ok and l_ok:
        # Busca rodou nos dois canais e nao ha ebook/arquivo digital:
        # escanear o fisico que o William tem e a via (comprar IMPRESSO nao
        # faz sentido: ele ja tem o livro).
        reg["veredito"] = "sem_digital_compravel"
        reg["vias"] = []
        if imp_loja:
            reg["versoes_impressas_disponiveis"] = [
                {"loja": l.get("loja_nome"), "url": l.get("url")} for l in imp_loja[:5]
            ]
    else:
        # A busca nao rodou (rede/engine) — NAO pode virar "sem digital".
        reg["veredito"] = "indeterminado"
        reg["vias"] = []

    reg["proxima_via"] = {
        "existe_digital_compravel": "via_2_comprar_digital",
        "sem_digital_compravel": "via_3_escanear_fisico",
        "indeterminado": "repetir_busca_antes_de_escanear",
    }[reg["veredito"]]

    with _lock:
        with SAIDA.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(reg, ensure_ascii=False) + "\n")
    return reg


def carregar_fila():
    import yaml
    doc = yaml.safe_load(TRIAGEM.read_text(encoding="utf-8")) or {}
    fila = []
    for e in (doc.get("vias", {}).get("via_2_escanear") or []):
        fila.append({
            "titulo": e.get("titulo"),
            "autor": e.get("autor") or "",
            "slug": e.get("slug"),
            "origem": "gap",
            "onde": (e.get("exemplar_fisico") or {}).get("biblioteca"),
        })
    for e in (doc.get("via_2b_escanear_fora_do_canon") or []):
        fila.append({
            "titulo": e.get("titulo"),
            "autor": e.get("autor") or "",
            "slug": e.get("slug"),
            "origem": e.get("origem"),
            "onde": e.get("onde"),
        })
    # BUG 2026-11-07: as filas "AGUARDANDO VERIFICACAO" nunca entravam na fila
    # do verificador — so as ja-classificadas. Resultado: os fisicos que a
    # triagem marcou como "verificar antes de escanear" ficavam para sempre
    # sem verificacao (o Carpeaux ficou assim). A verificacao e o que decide
    # escanear-vs-comprar-digital: sem ela, a triagem nao anda.
    for chave in ("via_3b_aguardando_verificacao",):
        for e in (doc.get("vias", {}).get(chave) or []):
            ex = e.get("exemplar_fisico") or {}
            fila.append({
                "titulo": e.get("titulo"),
                "autor": e.get("autor") or "",
                "slug": None,
                "origem": "gap",
                "onde": ex.get("biblioteca"),
            })
    for e in (doc.get("via_2b_aguardando_verificacao") or []):
        fila.append({
            "titulo": e.get("titulo"),
            "autor": e.get("autor") or "",
            "slug": e.get("slug"),
            "origem": e.get("origem"),
            "onde": e.get("onde"),
        })
    return fila


def ja_feitos():
    """Itens ja verificados (retomada)."""
    feitos = {}
    if SAIDA.exists():
        for ln in SAIDA.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:
                continue
            feitos[(norm(r.get("titulo") or ""), norm(r.get("autor") or ""))] = r
    return feitos


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--forcar", action="store_true", help="reverifica mesmo os ja feitos")
    ap.add_argument("--limite", type=int, default=None)
    ap.add_argument("--apenas", default=None, help="filtrar por titulo (substring)")
    ap.add_argument("--threads", type=int, default=3)
    args = ap.parse_args()

    fila = carregar_fila()
    if args.apenas:
        alvo = norm(args.apenas)
        fila = [f for f in fila if alvo in norm(f["titulo"])]
    feitos = {} if args.forcar else ja_feitos()
    pend = [f for f in fila
            if args.forcar or (norm(f["titulo"]), norm(f.get("autor") or "")) not in feitos]
    if args.limite:
        pend = pend[: args.limite]

    print(f"[fila] {len(fila)} | a verificar: {len(pend)} | ja feitos: {len(feitos)}",
          file=sys.stderr)
    if not pend:
        print(json.dumps({"fila": len(fila), "verificados_agora": 0,
                          "resumo": resumo(feitos)}, ensure_ascii=False, indent=2))
        return

    contagem = {"existe_digital_compravel": 0, "sem_digital_compravel": 0,
                "indeterminado": 0}
    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        for i, reg in enumerate(ex.map(processar, pend), 1):
            contagem[reg["veredito"]] = contagem.get(reg["veredito"], 0) + 1
            print(f"  [{i}/{len(pend)}] {reg['veredito']:26} {reg['titulo'][:60]}",
                  file=sys.stderr)
            feitos[(norm(reg["titulo"]), norm(reg.get("autor") or ""))] = reg

    print(json.dumps({"fila": len(fila), "verificados_agora": len(pend),
                      "resumo": resumo(feitos)}, ensure_ascii=False, indent=2))


def resumo(feitos):
    r = {"existe_digital_compravel": [], "sem_digital_compravel": [],
         "indeterminado": []}
    for k, v in feitos.items():
        ver = v.get("veredito")
        if ver in r:
            r[ver].append(v.get("titulo"))
    return {k: len(v) for k, v in r.items()}


if __name__ == "__main__":
    main()
