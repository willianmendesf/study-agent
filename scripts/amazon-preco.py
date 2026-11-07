#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
amazon-preco.py — extrai PRECO e FORMATO reais das paginas de produto da Amazon.

Por que existe:
  A Amazon bloqueia `web_fetch` (devolve "Clique no bouton para continuar
  comprando"), mas responde a `curl` com User-Agent de navegador (200,
  ~1,4 MB). Com isso da para ler o preco real e o formatodisponivel
  (Kindle / capa mole / capa dura) do link - que e o que o William precisa
  para decidir o que comprar.

NAO compra. NAO faz login. NAO faz pedido. SO LE.

Uso:
  python3 scripts/amazon-preco.py https://www.amazon.com.br/X-dp/YYYYYYYYYY
  python3 scripts/amazon-preco.py --arquivo data/perfil/bibliotecario/catalogo-compras.yaml
"""
import argparse
import json
import re
import sys
import time
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Headers completos de navegador: sem o Accept-Language a Amazon pode
# redirecionar para a pagina de captcha (503 no curl puro).
HEADERS = {
    "User-Agent": UA,
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

TIMEOUT = 30


def _tx(html, pattern):
    m = re.search(pattern, html, re.S)
    return m.group(1).strip() if m else None


def precos(html):
    """Preco 'a-offscreen' (o visivel) e preco Amazon (o 'priceAmount')."""
    out = {}
    off = re.findall(r'a-offscreen">\s*R\$\s*([\d.,]+)', html)
    if off:
        out["preco_brl"] = off[0]
    amt = re.findall(r'"priceAmount"\s*:\s*([\d.]+)', html)
    if amt:
        out["preco_numerico"] = amt[0]
    else:
        whole = _tx(html, r'a-price-whole"[^>]*>([\d.,]+)')
        frac = _tx(html, r'a-price-fraction"[^>]*>([\d.,]+)')
        if whole:
            out["preco_numerico"] = f"{whole}.{frac}" if frac else whole
    return out


def formatos(html):
    """Formatosこのページ: Kindle / capa mole / capa dura / ebook."""
    achados = []
    if "kindle" in html.lower():
        achados.append("Kindle (digital)")
    if re.search(r"capa\s*mole|paperback", html, re.I):
        achados.append("capa mole")
    if re.search(r"capa\s*dura|hardcover", html, re.I):
        achados.append("capa dura")
    if re.search(r"ebook\s*digital|kindle\s*edition", html, re.I):
        if "Kindle (digital)" not in achados:
            achados.append("Kindle (digital)")
    # #de volumes / #de paginas
    pgs = re.findall(r'(\d+)\s*p[áa]ginas', html)
    if pgs:
        achados.append(f"{max(int(p) for p in pgs)} páginas")
    return achados


def titulo(html):
    return _tx(html, r'id="productTitle"[^>]*>\s*(.*?)\s*</span>')


def autor(html):
    a = re.findall(r'id="bylineInfo"[^>]*>(.*?)</a>', html, re.S)
    if a:
        t = re.sub(r"<[^>]+>", "", a[0])
        t = re.sub(r"\s+", " ", t).strip()
        t = re.sub(r"^(Por|por|by)\s+", "", t)
        return t
    return None


def disponivel(html):
    if re.search(r"Currently unavailable|Indispon[íi]vel no momento|Sem estoque", html, re.I):
        return "indisponivel"
    if re.search(r'"availability"\s*:\s*"[^"]*(out_of_stock|unavailable)', html, re.I):
        return "indisponivel"
    if re.search(r'Em estoque|Dispon[íi]vel|Add to Cart|Comprar', html, re.I):
        return "disponivel"
    return "desconhecido"


def ler(url, tentativas=3):
    """Le a pagina. A Amazon devolve 503 (bot) com frequencia: ha backoff
    e, em ultimo caso, tenta o host sem 'www.'."""
    html = None
    erro = None
    espera = 10
    alvos = [url]
    m = re.match(r"(https://)www\.(amazon\.com\.br/.*)", url)
    if m:
        alvos.append(m.group(1) + m.group(2))
    for alvo in alvos:
        for tent in range(tentativas):
            req = urllib.request.Request(alvo, headers=HEADERS)
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    html = r.read().decode("utf-8", "replace")
                break
            except Exception as e:
                erro = f"{alvo} -> {e}"
                if tent < tentativas - 1:
                    time.sleep(espera)
                    espera *= 2
        if html:
            break
    if not html:
        return {"url": url, "erro": erro}
    d = {"url": url, "titulo": titulo(html), "autor": autor(html)}
    d.update(precos(html))
    d["formatos"] = formatos(html)
    d["disponibilidade"] = disponivel(html)
    return d


def do_arquivo(path):
    import yaml
    doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
    n = 0
    for obra in doc.get("obras", []) or []:
        for loja in obra.get("lojas", []) or []:
            if loja.get("loja") != "amazon":
                continue
            r = ler(loja["url"])
            if r.get("erro"):
                print(f"  ERRO {obra['titulo']}: {r['erro']}", file=sys.stderr)
                continue
            loja["preco_brl"] = r.get("preco_brl")
            loja["preco_numerico"] = r.get("preco_numerico")
            loja["formatos"] = r.get("formatos")
            loja["disponibilidade"] = r.get("disponibilidade")
            loja["titulo_real_loja"] = r.get("titulo")
            loja["autor_real_loja"] = r.get("autor")
            loja["preco_verificado_em"] = time.strftime("%Y-%m-%d")
            print(f"  {obra['titulo'][:42]:42} {str(r.get('preco_brl')):>10} "
                  f"{r.get('disponibilidade')} {' / '.join(r.get('formatos') or [])[:50]}")
            n += 1
            time.sleep(2.5)
    doc["precos_verificados"] = n
    doc["precos_verificados_em"] = time.strftime("%Y-%m-%d")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# catalogo-compras.yaml — GERADO por scripts/catalogo-compras.py — nao editar a mao\n")
        f.write(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=4096))
    print(f"[amazon-preco] {n} link(s) verificado(s) -> {path}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("--arquivo")
    args = ap.parse_args()
    if args.arquivo:
        do_arquivo(args.arquivo)
        return 0
    if args.url:
        print(json.dumps(ler(args.url), ensure_ascii=False, indent=1))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
